"""Debug-værktøj: henter jobsites og logger status, JSON-kald og tekst, så adaptere kan skrives."""
import asyncio
import re
import sys

from playwright.async_api import async_playwright


async def probe(browser, url):
    print(f"\n===== {url}")
    page = await browser.new_page(locale="da-DK")
    calls = []

    async def on_response(resp):
        ct = resp.headers.get("content-type", "")
        if ("json" in ct or "xml" in ct) and resp.request.resource_type in ("xhr", "fetch", "document"):
            try:
                body = await resp.text()
            except Exception:
                body = ""
            calls.append((resp.request.method, resp.url, resp.status, len(body), body[:2500], resp.request.post_data))

    page.on("response", on_response)
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        print("status", resp.status if resp else None, "final", page.url)
    except Exception as e:
        print("GOTO ERROR", e)
    await page.wait_for_timeout(2000)
    for m, u, s, n, b, pd in calls:
        print("CALL", m, s, u, n, "POST:", (pd or "")[:500])
        print("  BODY", b.replace("\n", " ")[:2500])
    try:
        links = await page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        jobish = [l for l in dict.fromkeys(links) if re.search(r"job|stilling|vis-job|annonce", l, re.I)]
        print("LINKS", len(links), jobish[:25])
        html = await page.content()
        print("HTML", len(html), re.sub(r"\s+", " ", html)[:1500])
        text = await page.inner_text("body")
        print("TEXT", re.sub(r"\s+", " ", text)[:2500])
    except Exception as e:
        print("READ ERROR", e)
    await page.close()


async def main(urls):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for u in urls:
            await probe(browser, u)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
