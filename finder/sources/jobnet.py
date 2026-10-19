"""Jobnet: den offentlige søgning har et JSON-endpoint med hele opslagsteksten."""
from datetime import datetime, timedelta, timezone

from ..http import get
from ..job import Job
from ..text import html_to_text

URL = "https://jobnet.dk/bff/FindJob/Search"
PER_PAGE = 100
MAX_PAGES = 3
MAX_AGE_DAYS = 7


def _recent(ad):
    d = ad.get("publicationDate")
    if not d:
        return True
    try:
        dt = datetime.fromisoformat(d.replace("Z", "+00:00"))
    except ValueError:
        return True
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt >= datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)


def _job(ad, query):
    title = (ad.get("title") or ad.get("occupation") or "").strip()
    kind = (ad.get("jobAnnouncementTypeName") or "").lower()
    temporary = True if any(w in kind for w in ("tidsbegr", "vikar", "midlertid")) else None
    pc = ad.get("postalCode")
    return Job(
        source="Jobnet",
        id=ad["jobAdId"],
        title=title,
        company=(ad.get("hiringOrgName") or "").strip(),
        url=f"https://jobnet.dk/find-job/{ad['jobAdId']}",
        location=" ".join(str(x) for x in (pc, ad.get("postalDistrictName")) if x),
        postcode=int(pc) if str(pc or "").isdigit() else None,
        text=html_to_text(ad.get("description") or ""),
        hours="deltid" if ad.get("workHourPartTime") else "fuldtid",
        temporary=temporary,
        deadline=(ad.get("applicationDeadline") or "")[:10] or None,
        posted=(ad.get("publicationDate") or "")[:10] or None,
        detail_url=ad.get("jobAdUrl"),
        query=query,
    )


def fetch(queries, seen):
    jobs = {}
    for q in queries:
        for page in range(1, MAX_PAGES + 1):
            data = get(URL, params={
                "resultsPerPage": PER_PAGE, "pageNumber": page, "orderType": "PublicationDate",
                "searchString": q, "postalCode": 8000, "kmRadius": 80,
            }).json()
            ads = data.get("jobAds") or []
            recent = [a for a in ads if _recent(a)]
            for a in recent:
                jobs.setdefault(a["jobAdId"], _job(a, q))
            if len(ads) < PER_PAGE or len(recent) < len(ads):
                break
    return list(jobs.values())
