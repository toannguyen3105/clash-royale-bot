import time
from core.adb import ADBInterface
from vision.detector import Detector
from utils.logger import logger
from config import config

# Bottom nav "Battle" icon, used to back out of other screens (e.g. Shop) to the Lobby.
# Tied to the current device's resolution (1080x2400), same as the vision templates.
BATTLE_NAV_ICON = (592, 2340)
MAX_LOBBY_RETURN_ATTEMPTS = 3


def ensure_at_lobby():
    """Confirm the Lobby screen is showing, backing out via the Battle nav icon if not
    (e.g. launch_app() skipped launching because the app was already in the foreground,
    but sitting on some other screen like Shop)."""
    for attempt in range(1, MAX_LOBBY_RETURN_ATTEMPTS + 1):
        ADBInterface.capture_screen(config.SCREENSHOT_PATH)
        if Detector.is_present(config.SCREENSHOT_PATH, config.TEMPLATE_PATH, config.THRESHOLD):
            return True
        logger.info(f"Not at Lobby yet, tapping Battle nav icon (attempt {attempt}/{MAX_LOBBY_RETURN_ATTEMPTS})...")
        ADBInterface.tap(*BATTLE_NAV_ICON)
        time.sleep(2)

    return False
