"""Send beskeder til Magnus via Telegram-botten."""
import os
import time

import requests

API = "https://api.telegram.org/bot{token}/{method}"


def _call(method, **params):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN mangler")
    r = requests.post(API.format(token=token, method=method), json=params, timeout=30)
    if r.status_code == 429:
        time.sleep(r.json().get("parameters", {}).get("retry_after", 5) + 1)
        return _call(method, **params)
    r.raise_for_status()
    return r.json()["result"]


def discover_chat_id() -> int | None:
    """Find chat-id ud fra den seneste besked nogen har skrevet til botten."""
    me = _call("getMe")
    updates = _call("getUpdates", limit=100)
    print(f"Telegram: bot @{me.get('username')}, {len(updates)} ventende beskeder")
    for u in reversed(updates):
        msg = u.get("message") or u.get("edited_message")
        if msg:
            return msg["chat"]["id"]
    return None


def send(chat_id: int, text: str):
    _call("sendMessage", chat_id=chat_id, text=text[:4096], parse_mode="HTML", disable_web_page_preview=True)
    time.sleep(1.1)
