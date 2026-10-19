"""Regelbaseret filtrering og udfyldning af arbejdstid/ansættelsestype ud fra teksten."""
import re

from . import config as C
from .job import Job


def postcode_ok(pc: int) -> bool:
    return any(lo <= pc <= hi for lo, hi in C.ALLOWED_POSTCODES)


def location_ok(job: Job) -> bool:
    if job.source == "LinkedIn":
        return True  # søgningen er allerede begrænset til 80 km fra Aarhus
    if job.postcode:
        return postcode_ok(job.postcode)
    loc = job.location or ""
    # flere byer ("Aarhus, Silkeborg eller Kolding"): ok hvis bare én er inden for området
    return bool(C.ALLOWED_TOWNS.search(loc)) or not loc


def title_reason(title: str) -> str | None:
    if C.EXCLUDE_TITLE.search(title):
        return "titel: " + C.EXCLUDE_TITLE.search(title).group(0)
    if C.MANAGER.search(title) and not C.JUNIOR.search(title):
        return "titel: manager"
    if not C.RELEVANT_TITLE.search(title):
        return "titel ikke relevant"
    return None


def reject_reason(job: Job) -> str | None:
    if job.exclude:
        return job.exclude
    r = title_reason(job.title)
    if r:
        return r
    if not location_ok(job):
        return f"område: {job.location or job.postcode}"
    m = C.TOO_MUCH_EXPERIENCE.search(job.text or "")
    if m:
        return "erfaring: " + m.group(0).strip()[:60]
    if C.STUDY_JOB.search(f"{job.title}\n{job.text}"):
        return "studiejob/praktik"
    return None


def fill_from_text(job: Job):
    blob = f"{job.title}\n{job.text}"
    if job.temporary is None and C.TEMPORARY.search(blob):
        job.temporary = True
    if job.hours is None:
        if C.PART_TIME.search(blob):
            job.hours = "deltid"
        elif C.FULL_TIME.search(blob):
            job.hours = "fuldtid"


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9æøå]+", " ", (s or "").lower()).strip()


def dedupe_key(job: Job) -> str:
    company = re.sub(r"\b(a/?s|aps|i/?s|p/?s|group|danmark|denmark)(?!\w)", "", (job.company or "").lower())
    return f"{norm(job.title)}|{norm(company)}"
