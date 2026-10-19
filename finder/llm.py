"""Valgfri vurdering med Claude. Bruges kun når ANTHROPIC_API_KEY er sat."""
import json
import os

from . import config as C
from .job import Job

SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer", "description": "1-10: hvor realistisk og relevant jobbet er for kandidaten"},
        "arbejdstid": {"type": "string", "enum": ["fuldtid", "deltid", "ukendt"]},
        "ansaettelse": {"type": "string", "enum": ["tidsbegrænset", "fast", "ukendt"]},
        "periode": {"type": "string", "description": "Fx 'barselsvikariat til aug. 2027'. Tom hvis ukendt eller fast."},
        "by": {"type": "string", "description": "Byen hvor jobbet udføres"},
        "begrundelse": {"type": "string", "description": "Én kort sætning på dansk (højst 25 ord) til kandidaten i du-form om hvorfor scoren er som den er"},
    },
    "required": ["score", "arbejdstid", "ansaettelse", "periode", "by", "begrundelse"],
    "additionalProperties": False,
}

_client = None


def enabled() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def assess(job: Job) -> dict:
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()
    ad = (
        f"Titel: {job.title}\nVirksomhed: {job.company}\nSted: {job.location}\n"
        f"Arbejdstid ifølge jobsitet: {job.hours or 'ikke angivet'}\n"
        f"Tidsbegrænset ifølge jobsitet: {'ja' if job.temporary else 'nej' if job.temporary is False else 'ikke angivet'}\n\n"
        f"{(job.text or '')[:12000]}"
    )
    resp = _client.messages.create(
        model=C.LLM_MODEL,
        max_tokens=4000,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        system=(
            "Du vurderer jobopslag for en jobsøgende. Vær realistisk: scor lavt hvis opslaget kræver mere erfaring, "
            "uddannelse eller ledelse end kandidaten har, eller hvis det er butik, studiejob eller praktik. "
            "Scor højt hvis kandidaten realistisk kan blive kaldt til samtale. Skriv begrundelsen direkte til kandidaten i du-form.\n\n" + C.PROFILE
        ),
        messages=[{"role": "user", "content": ad}],
    )
    print(f"  LLM: {resp.model}, {resp.usage.input_tokens} ind / {resp.usage.output_tokens} ud tokens")
    if resp.stop_reason == "refusal":
        raise RuntimeError("LLM afviste opslaget")
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text)
