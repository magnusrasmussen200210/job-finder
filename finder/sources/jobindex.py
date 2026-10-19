"""Jobindex: søgesiden indeholder resultaterne som JSON i `Stash = {...}`."""
import json

from ..http import get
from ..job import Job
from ..text import html_to_text

URL = "https://www.jobindex.dk/jobsoegning"
# Region Midtjylland, Vejle og Fredericia kommune
GEOAREAS = [2, 100, 26]
MAX_PAGES = 3


def _search(query, page=1, **filters):
    params = {"q": query, "geoareaid": GEOAREAS, "jobage": 7, "sort": "date", "page": page, **filters}
    h = get(URL, params=params).text
    i = h.find("Stash =")
    if i < 0:
        raise RuntimeError("Jobindex: fandt ikke Stash på søgesiden")
    stash, _ = json.JSONDecoder().raw_decode(h[i + len("Stash ="):].lstrip())
    resp = stash["jobsearch/result_app/list"]["storeData"]["searchResponse"]
    return resp["results"], resp.get("total_pages") or 1


def _search_all(query, stop=None, **filters):
    out = []
    page = 1
    while True:
        results, total = _search(query, page, **filters)
        out += results
        if page >= min(total, MAX_PAGES) or not results or (stop and stop(results)):
            return out
        page += 1


def _job(r, query):
    addresses = r.get("addresses") or []
    postcode = next((int(a["zipcode"]) for a in addresses if str(a.get("zipcode", "")).isdigit()), None)
    company = (r.get("company") or {}).get("name") or r.get("companytext") or ""
    return Job(
        source="Jobindex",
        id=r["tid"],
        title=(r.get("headline") or "").strip(),
        company=company.strip(),
        url=r.get("share_url") or f"https://www.jobindex.dk/vis-job/{r['tid']}",
        location=r.get("area") or ", ".join(a.get("city", "") for a in addresses),
        postcode=postcode,
        text=html_to_text(r.get("html") or ""),
        deadline=None if r.get("apply_deadline_asap") else r.get("lastdate"),
        posted=r.get("firstdate"),
        detail_url=r.get("url"),
        query=query,
    )


def fetch(queries, seen):
    jobs = {}
    for q in queries:
        # stop pagineringen når en hel side kun indeholder job vi har set før
        results = _search_all(q, stop=lambda rs: all(f"Jobindex:{r['tid']}" in seen for r in rs))
        for r in results:
            jobs.setdefault(r["tid"], _job(r, q))
    return list(jobs.values())


def label(jobs):
    """Find arbejdstid og ansættelsestype via Jobindex' egne filtre, kun for de job der skal sendes."""
    by_query = {}
    for j in jobs:
        by_query.setdefault(j.query, []).append(j)
    for q, js in by_query.items():
        wanted = {j.id for j in js}
        sets = {}
        for name, flt in {
            "fuldtid": {"workinghours_type": 1},
            "deltid": {"workinghours_type": 2},
            "fast": {"employment_type": 1},
            "tidsbegrænset": {"employment_type": 2},
            "frivillig": {"employment_type": 9},
        }.items():
            sets[name] = {r["tid"] for r in _search_all(q, **flt)} & wanted
        for j in js:
            if j.id in sets["frivillig"]:
                j.exclude = "frivillig"
            if j.id in sets["deltid"]:
                j.hours = "deltid"
            elif j.id in sets["fuldtid"]:
                j.hours = "fuldtid"
            if j.id in sets["tidsbegrænset"]:
                j.temporary = True
            elif j.id in sets["fast"]:
                j.temporary = False
