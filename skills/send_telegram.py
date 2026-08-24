#!/usr/bin/env python3
"""
Send the latest data/message.txt to Telegram via the PhDork bot.
Reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from environment,
falling back to a local .env file for local runs.
"""

import os
import requests
from pathlib import Path

def load_env_file(path='.env'):
    """Minimal .env loader — no extra dependency needed."""
    if not Path(path).exists():
        return
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip())

load_env_file()

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

if not BOT_TOKEN or not CHAT_ID:
    raise SystemExit(
        "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID.\n"
        "Set them as environment variables, or create skills/.env "
        "(see .env.example)."
    )

message_path = Path('data/message.txt')
if not message_path.exists():
    raise SystemExit("data/message.txt not found — run build_message.py first.")

message = message_path.read_text()

# Telegram messages have a 4096-character limit; split if needed.
MAX_LEN = 4000

def chunk(text, size):
    for i in range(0, len(text), size):
        yield text[i:i + size]

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

for part in chunk(message, MAX_LEN):
    resp = requests.post(url, data={"chat_id": CHAT_ID, "text": part})
    if resp.status_code != 200:
        print(f"✗ Failed to send: {resp.status_code} {resp.text}")
    else:
        print("✓ Sent chunk to Telegram")
