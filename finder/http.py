"""Fælles HTTP-session med browser-agtig User-Agent og høflige pauser."""
import time

import requests

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
session = requests.Session()
session.headers.update({"User-Agent": UA, "Accept-Language": "da-DK,da;q=0.9,en;q=0.8"})


def get(url, params=None, pause=1.0, **kw):
    time.sleep(pause)
    for attempt in range(3):
        r = session.get(url, params=params, timeout=30, **kw)
        if r.status_code in (429, 502, 503) and attempt < 2:
            time.sleep(10 * (attempt + 1))
            continue
        r.raise_for_status()
        return r
