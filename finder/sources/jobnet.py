"""Jobnet: den offentlige søgning har et JSON-endpoint med hele opslagsteksten."""
from datetime import datetime, timedelta, timezone

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


def _search_all(queries):
    """Jobnets BFF ligger bag en JS-udfordring (myracloud), så søgningen køres i en rigtig browser.
    Siden laver selv kaldet til /bff/FindJob/Search; vi omskriver parametrene og læser svaret."""
    from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

    from playwright.sync_api import sync_playwright

    wanted = {}
    results = {}

    def rewrite(route):
        parts = urlsplit(route.request.url)
        qs = {k: v[0] for k, v in parse_qs(parts.query).items()}
        qs.update(wanted)
        route.continue_(url=urlunsplit(parts._replace(query=urlencode(qs))))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(locale="da-DK")
        page.route("**/bff/FindJob/Search*", rewrite)
        for q in queries:
            for n in range(1, MAX_PAGES + 1):
                wanted.clear()
                wanted.update({"resultsPerPage": PER_PAGE, "pageNumber": n, "orderType": "PublicationDate", "searchString": q})
                with page.expect_response(lambda r: "/bff/FindJob/Search" in r.url, timeout=45000) as resp:
                    page.goto(f"https://jobnet.dk/find-job?searchString={q}", wait_until="domcontentloaded", timeout=45000)
                r = resp.value
                if r.status != 200:
                    raise RuntimeError(f"Jobnet svarede {r.status} for '{q}'")
                ads = r.json().get("jobAds") or []
                recent = [a for a in ads if _recent(a)]
                results.setdefault(q, []).extend(recent)
                if len(ads) < PER_PAGE or len(recent) < len(ads):
                    break
        browser.close()
    return results


def fetch(queries, seen):
    jobs = {}
    for q, ads in _search_all(queries).items():
        for a in ads:
            jobs.setdefault(a["jobAdId"], _job(a, q))
    return list(jobs.values())
