import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Centralized configuration for the bot."""
    PACKAGE_NAME = os.getenv("PACKAGE_NAME", "com.supercell.clashroyale")
    TEMPLATE_PATH = os.getenv("TEMPLATE_PATH", "assets/templates/battle_button.png")
    SCREENSHOT_PATH = os.getenv("SCREENSHOT_PATH", "assets/debug/screen.png")
    LOG_FILE = os.getenv("LOG_FILE", "bot.log")
    THRESHOLD = float(os.getenv("THRESHOLD", 0.8))
    DEVICE_SERIAL = os.getenv("DEVICE_SERIAL", "")
    DEVICE_PIN = os.getenv("DEVICE_PIN", "")
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
    MAX_GOLD_PRICE = int(os.getenv("MAX_GOLD_PRICE", 2000))
    RESTART_APP_ON_START = os.getenv("RESTART_APP_ON_START", "true").strip().lower() in ("1", "true", "yes", "on")

# Global config instance
config = Config()
