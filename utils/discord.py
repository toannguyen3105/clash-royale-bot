import json
import urllib.request
import urllib.error
from utils.logger import logger
from config import config

def send_discord_message(content):
    """Post a simple text message to config.DISCORD_WEBHOOK_URL. No-op if unset."""
    if not config.DISCORD_WEBHOOK_URL:
        return

    payload = json.dumps({"content": content}).encode("utf-8")
    request = urllib.request.Request(
        config.DISCORD_WEBHOOK_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "clash-royale-bot (https://github.com, 1.0)",
        },
    )
    try:
        urllib.request.urlopen(request, timeout=10)
    except urllib.error.URLError as e:
        logger.error(f"Failed to send Discord notification: {e}")
