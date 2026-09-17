import pytest
from unittest.mock import patch
from utils.discord import send_discord_message
from config import config


def test_send_discord_message_noop_when_unset():
    """Test send_discord_message does nothing when DISCORD_WEBHOOK_URL is unset."""
    with patch.object(config, "DISCORD_WEBHOOK_URL", ""), \
         patch("urllib.request.urlopen") as mock_urlopen:
        send_discord_message("hello")

        mock_urlopen.assert_not_called()


def test_send_discord_message_success():
    """Test send_discord_message posts to the configured webhook URL."""
    with patch.object(config, "DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/123/abc"), \
         patch("urllib.request.urlopen") as mock_urlopen:
        send_discord_message("hello")

        mock_urlopen.assert_called_once()


def test_send_discord_message_malformed_url_does_not_raise():
    """Test send_discord_message catches a malformed webhook URL instead of crashing."""
    with patch.object(config, "DISCORD_WEBHOOK_URL", "not-a-valid-url"), \
         patch("urllib.request.urlopen") as mock_urlopen:
        send_discord_message("hello")  # must not raise

        mock_urlopen.assert_not_called()
