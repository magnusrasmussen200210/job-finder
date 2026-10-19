"""LinkedIn: gæste-API'et (uden login) giver søgeresultater og opslag som HTML-fragmenter."""
import re

from ..http import get
from ..job import Job
from ..text import html_to_text

SEARCH = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"
PAGES = 2  # 10 resultater pr. side


def _cards(html):
    for li in re.split(r"<li\b", html)[1:]:
        m = re.search(r"urn:li:jobPosting:(\d+)", li)
        if not m:
            continue

        def cls(name):
            mm = re.search(rf'class="[^"]*{name}[^"]*"[^>]*>(.*?)</', li, re.S)
            return html_to_text(mm.group(1)) if mm else ""

        date = re.search(r'<time[^>]*datetime="([^"]+)"', li)
        yield Job(
            source="LinkedIn",
            id=m.group(1),
            title=cls("base-search-card__title"),
            company=cls("base-search-card__subtitle"),
            url=f"https://www.linkedin.com/jobs/view/{m.group(1)}",
            location=cls("job-search-card__location"),
            posted=date.group(1) if date else None,
        )


def fetch(queries, seen):
    jobs = {}
    for q in queries:
        for page in range(PAGES):
            html = get(SEARCH, params={
                "keywords": q, "location": "Aarhus, Central Denmark Region, Denmark", "distance": 50,
                "f_TPR": "r604800", "f_JT": "F,P,C,T,O", "start": page * 10,
            }, pause=2).text
            cards = list(_cards(html))
            for j in cards:
                j.query = q
                jobs.setdefault(j.id, j)
            if len(cards) < 10:
                break
    return list(jobs.values())


def details(job):
    """Hent opslagstekst, ansættelsestype og evt. ekstern ansøgningsside."""
    h = get(DETAIL.format(job.id), pause=2).text
    m = re.search(r'show-more-less-html__markup[^>]*>(.*?)</div>', h, re.S)
    if m:
        job.text = html_to_text(m.group(1))
    crit = re.search(r"description__job-criteria-list(.*?)</ul>", h, re.S)
    crit = html_to_text(crit.group(1)).lower() if crit else ""
    if re.search(r"deltid|part-time", crit):
        job.hours = "deltid"
    elif re.search(r"fuldtid|full-time", crit):
        job.hours = "fuldtid"
    if re.search(r"midlertidig|temporary|kontrakt|contract", crit):
        job.temporary = True
    if re.search(r"praktik|internship|frivillig|volunteer", crit):
        job.exclude = "praktik/frivillig"
