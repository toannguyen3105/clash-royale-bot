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

# Global config instance
config = Config()
