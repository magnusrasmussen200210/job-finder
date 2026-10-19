"""Henter nye job fra Jobindex, Jobnet og LinkedIn, frasorterer de urealistiske og sender resten på Telegram."""
import html
import json
import os
import sys
import traceback
from collections import Counter
from itertools import zip_longest
from datetime import date, timedelta
from pathlib import Path

from . import config as C
from . import llm, rules, telegram
from .http import get
from .sources import jobindex, jobnet, linkedin
from .text import html_to_text

STATE = Path(__file__).resolve().parent.parent / "state" / "seen.json"
MAX_SEND = 40          # resten sendes ved næste kørsel
KEEP_DAYS = 90
ERROR_ALERT_AFTER = 3  # advar på Telegram når en kilde har fejlet så mange kørsler i træk

SOURCES = [
    ("Jobindex", lambda seen: jobindex.fetch(C.QUERIES_DA, seen)),
    ("Jobnet", lambda seen: jobnet.fetch(C.QUERIES_DA, seen)),
    ("LinkedIn", lambda seen: linkedin.fetch(C.QUERIES_LINKEDIN, seen)),
]


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"seen": {}, "dedupe": {}, "chat_id": None, "errors": {}}


def save_state(state):
    cutoff = (date.today() - timedelta(days=KEEP_DAYS)).isoformat()
    for k in ("seen", "dedupe"):
        state[k] = {key: d for key, d in state[k].items() if d >= cutoff}
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1, ensure_ascii=False, sort_keys=True))


def full_text(job):
    """Hent hele opslaget til LLM-vurderingen, hvis vi kun har en teaser."""
    if len(job.text) >= 1500 or not job.detail_url:
        return
    try:
        t = html_to_text(get(job.detail_url, pause=0.5).text)
        if len(t) > len(job.text):
            job.text = t[:15000]
    except Exception as e:
        print(f"  kunne ikke hente {job.detail_url}: {e}")


def fmt_date(d):
    try:
        return date.fromisoformat(d[:10]).strftime("%d-%m-%Y")
    except (TypeError, ValueError):
        return d


def message(job, verdict=None):
    e = html.escape
    city = (verdict or {}).get("by") or job.location or "ikke angivet"
    hours = {"fuldtid": "Fuldtid", "deltid": "Deltid"}.get(job.hours, "Arbejdstid ikke angivet")
    if job.temporary:
        period = (verdict or {}).get("periode")
        kind = "Tidsbegrænset" + (f" ({period})" if period else "")
    elif job.temporary is False:
        kind = "Fast stilling"
    else:
        kind = "Ikke angivet om fast eller tidsbegrænset"
    lines = [
        f"<b>{e(job.title)}</b>",
        e(job.company),
        f"📍 {e(city)}",
        f"🕒 {hours}",
        f"📅 {e(kind)}",
    ]
    if job.deadline:
        lines.append(f"⏳ Frist: {fmt_date(job.deadline)}")
    if verdict:
        lines.append(f"⭐ {verdict['score']}/10: {e(verdict['begrundelse'])}")
    lines.append(f'🔗 <a href="{e(job.url, quote=True)}">Se opslaget på {job.source}</a>')
    return "\n".join(lines)


def main(argv):
    dry = "--dry-run" in argv
    verbose = "--verbose" in argv or dry
    state = load_state()
    today = date.today().isoformat()

    chat_id = os.environ.get("TELEGRAM_CHAT_ID") or state.get("chat_id")
    if not chat_id and not dry:
        chat_id = telegram.discover_chat_id()
        if not chat_id:
            print("Ingen chat fundet. Skriv en besked til botten på Telegram, så sendes jobbene ved næste kørsel.")
            return 0
        state["chat_id"] = chat_id
    alerts = []

    only = os.environ.get("KILDER", "").lower()
    jobs = []
    for name, fetch in SOURCES:
        if only and name.lower() not in only:
            continue
        try:
            found = fetch(state["seen"])
            print(f"{name}: {len(found)} job fundet")
            jobs += found
            state["errors"].pop(name, None)
        except Exception:
            traceback.print_exc()
            n = state["errors"][name] = state["errors"].get(name, 0) + 1
            if n == ERROR_ALERT_AFTER:
                alerts.append(f"⚠️ {name} har fejlet {n} kørsler i træk. Jobovervågningen kører videre med de andre sider.")

    new = [j for j in jobs if j.key not in state["seen"]]
    print(f"{len(new)} nye job")

    reasons = Counter()
    candidates = []
    run_keys = set()
    for j in new:
        r = rules.reject_reason(j)
        dk = rules.dedupe_key(j)
        if not r and (dk in state["dedupe"] or dk in run_keys):
            r = "dublet"
        if r:
            reasons[r.split(":")[0]] += 1
            if verbose:
                print(f"  fra: [{r}] {j.title} | {j.company} | {j.location} ({j.source})")
            state["seen"][j.key] = today
            continue
        run_keys.add(dk)
        candidates.append(j)
    print(f"Frasorteret: {dict(reasons)}; {len(candidates)} kandidater")

    by_source = {}
    for j in candidates:
        by_source.setdefault(j.source, []).append(j)
    mixed = [j for group in zip_longest(*by_source.values()) for j in group if j]
    candidates = mixed[:MAX_SEND]
    try:
        jobindex.label([j for j in candidates if j.source == "Jobindex"])
    except Exception:
        traceback.print_exc()
    for j in candidates:
        if j.source == "LinkedIn":
            try:
                linkedin.details(j)
            except Exception as ex:
                print(f"  LinkedIn-detaljer fejlede for {j.id}: {ex}")
        rules.fill_from_text(j)

    use_llm = llm.enabled()
    sent = 0
    for j in candidates:
        r = rules.reject_reason(j)  # LinkedIn-teksten kendes først nu
        if r:
            print(f"  fra efter detaljer: [{r}] {j.title} ({j.source})")
            state["seen"][j.key] = today
            continue
        verdict = None
        if use_llm:
            full_text(j)
            try:
                verdict = llm.assess(j)
            except Exception as ex:
                print(f"  LLM fejlede for {j.title}: {ex}")
            if verdict:
                if j.hours is None and verdict["arbejdstid"] != "ukendt":
                    j.hours = verdict["arbejdstid"]
                if j.temporary is None and verdict["ansaettelse"] != "ukendt":
                    j.temporary = verdict["ansaettelse"] == "tidsbegrænset"
                if verdict["score"] < C.LLM_MIN_SCORE:
                    print(f"  fra (LLM {verdict['score']}): {j.title} | {j.company}: {verdict['begrundelse']}")
                    state["seen"][j.key] = today
                    continue
        msg = message(j, verdict)
        if dry:
            print("\n" + msg)
        else:
            telegram.send(chat_id, msg)
            state["seen"][j.key] = today
            state["dedupe"][rules.dedupe_key(j)] = today
        sent += 1

    if not dry:
        for a in alerts:
            telegram.send(chat_id, a)
        save_state(state)
    print(f"Sendt: {sent}{' (dry run, intet sendt)' if dry else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
