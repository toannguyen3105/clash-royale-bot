import time
from core.adb import ADBInterface
from vision.detector import Detector
from utils.logger import logger
from utils.discord import send_discord_message
from config import config
from constants import SHOP_NAV_SETTLE_SECONDS, CLAIM_CONFIRM_DELAY_SECONDS

# Pixel coordinates below are tied to the current device's resolution (1080x2400),
# same constraint as the templates in assets/templates/.
SHOP_NAV_ICON = (130, 2340)
FREE_SLOT_CENTER = (185, 1175)
MAX_SHOP_NAV_ATTEMPTS = 3

DAILY_DEALS_BANNER_TEMPLATE = "assets/templates/shop_daily_deals_banner.png"
DAILY_DEAL_COLLECTED_BADGE_TEMPLATE = "assets/templates/daily_deal_collected_badge.png"


def _go_to_daily_deals():
    """Tap the Shop nav icon until the Daily Deals screen is detected (Shop remembers
    the last-viewed sub-tab, so a single tap doesn't reliably land there)."""
    for attempt in range(1, MAX_SHOP_NAV_ATTEMPTS + 1):
        ADBInterface.tap(*SHOP_NAV_ICON)
        time.sleep(SHOP_NAV_SETTLE_SECONDS)
        ADBInterface.capture_screen(config.SCREENSHOT_PATH)
        if Detector.is_present(config.SCREENSHOT_PATH, DAILY_DEALS_BANNER_TEMPLATE, config.THRESHOLD):
            return True
        logger.info(f"Daily Deals screen not found yet (attempt {attempt}/{MAX_SHOP_NAV_ATTEMPTS}).")

    logger.error("Could not navigate to the Daily Deals screen.")
    return False


def claim_free_daily_card():
    """Claim the free card slot in Market > Daily Deals, if not already claimed today."""
    if not _go_to_daily_deals():
        return False

    if Detector.is_present(config.SCREENSHOT_PATH, DAILY_DEAL_COLLECTED_BADGE_TEMPLATE, config.THRESHOLD):
        logger.info("Daily free card already claimed today.")
        send_discord_message("The free Daily Deals card has already been claimed today.")
        return False

    logger.info("Claiming free daily card...")
    ADBInterface.tap(*FREE_SLOT_CENTER)
    time.sleep(CLAIM_CONFIRM_DELAY_SECONDS)
    ADBInterface.capture_screen(config.SCREENSHOT_PATH)

    if Detector.is_present(config.SCREENSHOT_PATH, DAILY_DEAL_COLLECTED_BADGE_TEMPLATE, config.THRESHOLD):
        logger.info("[V] Daily free card claimed.")
        send_discord_message("Claimed the free Daily Deals card for today!")
        return True

    logger.error("Tapped the free slot but could not confirm it was claimed.")
    return False
