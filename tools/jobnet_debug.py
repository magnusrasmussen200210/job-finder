"""Midlertidigt: find ud af hvad Jobnets BFF kræver."""
import requests

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
s = requests.Session()
s.headers["User-Agent"] = UA
r = s.get("https://jobnet.dk/find-job")
print("page", r.status_code, dict(r.headers).get("set-cookie"))
for params in [
    "resultsPerPage=10&pageNumber=1&orderType=BestMatch&kmRadius=50&searchString=controller",
    "resultsPerPage=10&pageNumber=1&orderType=BestMatch&searchString=controller",
]:
    for hdr in [{}, {"Accept": "application/json", "Referer": "https://jobnet.dk/find-job?searchString=controller",
                     "X-Requested-With": "XMLHttpRequest", "Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "cors"}]:
        r = s.get("https://jobnet.dk/bff/FindJob/Search?" + params, headers=hdr)
        print(r.status_code, params[:60], list(hdr)[:2], dict(r.headers), r.text[:300])
