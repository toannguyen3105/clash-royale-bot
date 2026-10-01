import time
from core.adb import ADBInterface
from vision.detector import Detector
from utils.logger import logger
from config import config
from constants import LOBBY_NAV_SETTLE_SECONDS

# The bottom nav bar's layout depends on which tab is selected: the selected tab
# widens and pushes the other icons sideways, so the Battle icon has no fixed
# position (verified live: top-left x=385 with Social selected, x=557 with Shop
# or Collection selected). Locate it by template instead. The template is the
# unselected icon only -- once Battle is selected we're already at the Lobby.
BATTLE_NAV_ICON_TEMPLATE = "assets/templates/battle_nav_icon.png"

# The template is 140x120.
BATTLE_NAV_ICON_CENTER_OFFSET = (70, 60)

# Only matches inside the bottom nav bar count, so similar artwork elsewhere on
# screen can't be mistaken for the nav icon. Tied to the current device's
# resolution (1080x2400), same as the vision templates.
NAV_BAR_MIN_Y = 2200

# Last resort if the icon template can't be found (e.g. some unhandled popup
# covers the nav bar): the Battle icon's position while Battle is centered.
BATTLE_NAV_ICON_FALLBACK = (592, 2340)

# The clan chat's "New Messages" feed is a modal overlay whose OK bar covers the
# whole bottom nav bar, so no nav icon can be tapped until it's dismissed.
CHAT_OK_BUTTON_TEMPLATE = "assets/templates/chat_ok_button.png"
CHAT_OK_BUTTON = (540, 2330)

MAX_LOBBY_RETURN_ATTEMPTS = 3


def _find_battle_nav_icon():
    """Return the center of the Battle nav icon in the bottom nav bar, or None."""
    matches = Detector.find_all(config.SCREENSHOT_PATH, BATTLE_NAV_ICON_TEMPLATE, config.THRESHOLD)
    for x, y in matches:
        if y >= NAV_BAR_MIN_Y:
            return x + BATTLE_NAV_ICON_CENTER_OFFSET[0], y + BATTLE_NAV_ICON_CENTER_OFFSET[1]
    return None


def _is_at_lobby():
    ADBInterface.capture_screen(config.SCREENSHOT_PATH)
    return Detector.is_present(config.SCREENSHOT_PATH, config.TEMPLATE_PATH, config.THRESHOLD)


def ensure_at_lobby():
    """Confirm the Lobby screen is showing, backing out via the Battle nav icon if not
    (e.g. launch_app() skipped launching because the app was already in the foreground,
    but sitting on some other screen like Shop or Social)."""
    for attempt in range(1, MAX_LOBBY_RETURN_ATTEMPTS + 1):
        if _is_at_lobby():
            return True

        if Detector.is_present(config.SCREENSHOT_PATH, CHAT_OK_BUTTON_TEMPLATE, config.THRESHOLD):
            logger.info(f"Not at Lobby yet, dismissing the chat overlay covering the nav bar (attempt {attempt}/{MAX_LOBBY_RETURN_ATTEMPTS})...")
            ADBInterface.tap(*CHAT_OK_BUTTON)
            time.sleep(LOBBY_NAV_SETTLE_SECONDS)
            ADBInterface.capture_screen(config.SCREENSHOT_PATH)

        battle_icon = _find_battle_nav_icon()
        if battle_icon is None:
            logger.info("Battle nav icon not found in the nav bar, tapping its usual position instead.")
            battle_icon = BATTLE_NAV_ICON_FALLBACK

        logger.info(f"Not at Lobby yet, tapping Battle nav icon (attempt {attempt}/{MAX_LOBBY_RETURN_ATTEMPTS})...")
        ADBInterface.tap(*battle_icon)
        time.sleep(LOBBY_NAV_SETTLE_SECONDS)

    # Check once more: the last attempt's tap may have been the one that worked.
    return _is_at_lobby()
