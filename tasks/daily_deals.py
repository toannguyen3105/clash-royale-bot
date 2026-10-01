import time
from core.adb import ADBInterface
from vision.detector import Detector
from utils.logger import logger
from config import config
from constants import SHOP_NAV_SETTLE_SECONDS, CLAIM_CONFIRM_DELAY_SECONDS

# Pixel coordinates below are tied to the current device's resolution (1080x2400),
# same constraint as the templates in assets/templates/.
SHOP_NAV_ICON = (130, 2340)
FREE_SLOT_CENTER = (185, 1175)
# Re-tapping the Shop icon while already in Shop jumps to its next section, in a
# fixed 4-step cycle: Offers -> Market (Daily Deals) -> Cosmetics -> Currency ->
# Offers (verified live). One tap to enter Shop + up to 4 to go around the cycle.
MAX_SHOP_NAV_ATTEMPTS = 5

# Tapping the free slot opens a "Get X?" confirmation popup (even though it's
# free) with its own FREE! button that must be tapped to actually claim it. The
# popup's height depends on the card shown, so the button has no fixed position
# (e.g. y~1500 vs y~1613 seen live) -- tap the center of wherever its template
# matched instead. The template is 320x120.
CONFIRM_POPUP_BUTTON_CENTER_OFFSET = (160, 60)

# After confirming, the popup stays open showing "Purchased!" and hides the
# grid's "Collected" badge, so it has to be closed via its X button first. The
# template is 90x60.
POPUP_CLOSE_BUTTON_CENTER_OFFSET = (45, 30)

DAILY_DEALS_BANNER_TEMPLATE = "assets/templates/shop_daily_deals_banner.png"
DAILY_DEAL_COLLECTED_BADGE_TEMPLATE = "assets/templates/daily_deal_collected_badge.png"
DAILY_DEAL_CONFIRM_POPUP_TEMPLATE = "assets/templates/daily_deal_confirm_popup_button.png"
DAILY_DEAL_POPUP_CLOSE_BUTTON_TEMPLATE = "assets/templates/daily_deal_popup_close_button.png"


def go_to_daily_deals():
    """Tap the Shop nav icon until the Daily Deals screen is detected (each tap while
    in Shop jumps to the next section, so a single tap doesn't reliably land there).
    Checks the current screen first: if Daily Deals is already showing (e.g. right
    after claim_free_daily_card()), tapping Shop again would navigate away from it."""
    ADBInterface.capture_screen(config.SCREENSHOT_PATH)
    if Detector.is_present(config.SCREENSHOT_PATH, DAILY_DEALS_BANNER_TEMPLATE, config.THRESHOLD):
        return True

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
    """Claim the free card slot in Market > Daily Deals, if not already claimed today.
    Returns True once today's free card is collected (claimed now, or already
    earlier), False if that couldn't be confirmed."""
    if not go_to_daily_deals():
        return False

    if Detector.is_present(config.SCREENSHOT_PATH, DAILY_DEAL_COLLECTED_BADGE_TEMPLATE, config.THRESHOLD):
        logger.info("Daily free card already claimed today.")
        return True

    logger.info("Claiming free daily card...")
    ADBInterface.tap(*FREE_SLOT_CENTER)
    time.sleep(CLAIM_CONFIRM_DELAY_SECONDS)
    ADBInterface.capture_screen(config.SCREENSHOT_PATH)

    confirm_matches = Detector.find_all(config.SCREENSHOT_PATH, DAILY_DEAL_CONFIRM_POPUP_TEMPLATE, config.THRESHOLD)
    if confirm_matches:
        logger.info("Confirming claim in the popup...")
        x, y = confirm_matches[0]
        ADBInterface.tap(x + CONFIRM_POPUP_BUTTON_CENTER_OFFSET[0], y + CONFIRM_POPUP_BUTTON_CENTER_OFFSET[1])
        time.sleep(CLAIM_CONFIRM_DELAY_SECONDS)
        ADBInterface.capture_screen(config.SCREENSHOT_PATH)

    close_matches = Detector.find_all(config.SCREENSHOT_PATH, DAILY_DEAL_POPUP_CLOSE_BUTTON_TEMPLATE, config.THRESHOLD)
    if close_matches:
        x, y = close_matches[0]
        ADBInterface.tap(x + POPUP_CLOSE_BUTTON_CENTER_OFFSET[0], y + POPUP_CLOSE_BUTTON_CENTER_OFFSET[1])
        time.sleep(CLAIM_CONFIRM_DELAY_SECONDS)
        ADBInterface.capture_screen(config.SCREENSHOT_PATH)

    if Detector.is_present(config.SCREENSHOT_PATH, DAILY_DEAL_COLLECTED_BADGE_TEMPLATE, config.THRESHOLD):
        logger.info("[V] Daily free card claimed.")
        return True

    logger.error("Tapped the free slot but could not confirm it was claimed.")
    return False
