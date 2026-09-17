import json
import urllib.request
import urllib.error
from utils.logger import logger
from config import config
from constants import DISCORD_REQUEST_TIMEOUT_SECONDS

def send_discord_message(content):
    """Post a simple text message to config.DISCORD_WEBHOOK_URL. No-op if unset."""
    if not config.DISCORD_WEBHOOK_URL:
        return

    payload = json.dumps({"content": content}).encode("utf-8")
    try:
        request = urllib.request.Request(
            config.DISCORD_WEBHOOK_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "clash-royale-bot (https://github.com, 1.0)",
            },
        )
        urllib.request.urlopen(request, timeout=DISCORD_REQUEST_TIMEOUT_SECONDS)
    except (ValueError, urllib.error.URLError) as e:
        logger.error(f"Failed to send Discord notification: {e}")
