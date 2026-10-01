import time
from core.adb import ADBInterface
from vision.detector import Detector
from utils.logger import logger
from utils.discord import send_discord_message
from config import config
from constants import CLAIM_CONFIRM_DELAY_SECONDS
from tasks.daily_deals import go_to_daily_deals

GOLD_ICON_TEMPLATE = "assets/templates/gold_icon.png"
GEM_ICON_TEMPLATE = "assets/templates/gem_icon.png"
POPUP_CLOSE_BUTTON_TEMPLATE = "assets/templates/daily_deal_popup_close_button.png"
PURCHASED_BADGE_TEMPLATE = "assets/templates/daily_deal_purchased_badge.png"

# Known Daily Deals gold prices -> their template. Only prices captured here can
# ever be auto-bought; an unrecognized price is always skipped (never guessed).
# New price points show up over time -- capture a template and add it here.
KNOWN_GOLD_PRICE_TEMPLATES = {
    500: "assets/templates/daily_deal_price_500.png",
    800: "assets/templates/daily_deal_price_800.png",
    1200: "assets/templates/daily_deal_price_1200.png",
    1500: "assets/templates/daily_deal_price_1500.png",
    15000: "assets/templates/daily_deal_price_15000.png",
}

# "500" can partially match inside "1500" at the usual config.THRESHOLD (0.8):
# verified live, true matches score ~0.99-1.0, cross-matches ~0.85-0.88.
PRICE_MATCH_THRESHOLD = 0.95

# The gold/gem currency icon sits roughly this far right of the price digits'
# top-left match. This varies a bit with how many digits the price has (e.g.
# ~(205, 5) for "500" vs ~(226, 27) for "1500", verified live), so the
# proximity tolerance below has to be generous enough to cover that drift.
PRICE_TO_ICON_OFFSET = (205, 5)
ICON_PROXIMITY_TOLERANCE_PX = 30

# Icon template is 50x50; tapping its matched top-left directly can land right
# at the edge of the clickable pill button and miss (verified live -- a price-
# offset-based tap position missed entirely for a "1500" slot). Tapping the
# icon's own center is far more reliable since its position is what's actually
# confirmed as gold, not derived from a price-dependent offset.
ICON_CENTER_OFFSET = 25

# How close (in pixels) a "Purchased!" badge has to appear to where the price
# text used to be, to count as confirming that specific slot's purchase.
SLOT_TOLERANCE_PX = 100

# Confirmation popups render as a fixed-position modal over the viewport
# regardless of how far the background deals list has scrolled, so a gold/gem
# icon match in this Y band is inside the popup, not the dimmed background.
POPUP_REGION_Y_RANGE = (650, 1650)

# The currency icon renders slightly differently inside a popup than in the
# grid (scale/compression), so a true match there scores ~0.77-0.78 instead of
# the ~0.98-1.0 seen in the grid -- verified live on both a real gold and a
# real gem popup. Still a wide safety margin: the WRONG icon's template scores
# only ~0.02-0.08 at that same spot, so this threshold can't confuse them.
POPUP_ICON_THRESHOLD = 0.75

# Safety cap: at most this many paid slots exist on the Daily Deals grid.
MAX_SLOTS = 5

MAX_TAPS_TO_CLOSE_POPUP = 3


def _same_position(a, b, tolerance=ICON_PROXIMITY_TOLERANCE_PX):
    return abs(a[0] - b[0]) < tolerance and abs(a[1] - b[1]) < tolerance


def _icons_in_popup(icon_matches):
    return [(x, y) for x, y in icon_matches if POPUP_REGION_Y_RANGE[0] <= y <= POPUP_REGION_Y_RANGE[1]]


def _close_popup_if_open():
    for _ in range(MAX_TAPS_TO_CLOSE_POPUP):
        ADBInterface.capture_screen(config.SCREENSHOT_PATH)
        matches = Detector.find_all(config.SCREENSHOT_PATH, POPUP_CLOSE_BUTTON_TEMPLATE, 0.9)
        if not matches:
            return
        x, y = matches[0]
        ADBInterface.tap(x + 45, y + 30)
        time.sleep(CLAIM_CONFIRM_DELAY_SECONDS)


def _find_next_gold_slot(handled):
    """Return (price, tap_x, tap_y) for the first visible slot confirmed to be
    gold-priced (gold icon present, gem icon absent nearby) at or under
    config.MAX_GOLD_PRICE, excluding positions already in `handled`. Anything
    ambiguous is skipped, never guessed."""
    gold_icon_matches = Detector.find_all(config.SCREENSHOT_PATH, GOLD_ICON_TEMPLATE, config.THRESHOLD)
    gem_icon_matches = Detector.find_all(config.SCREENSHOT_PATH, GEM_ICON_TEMPLATE, config.THRESHOLD)

    for price, template in sorted(KNOWN_GOLD_PRICE_TEMPLATES.items()):
        if price > config.MAX_GOLD_PRICE:
            continue

        for price_pos in Detector.find_all(config.SCREENSHOT_PATH, template, PRICE_MATCH_THRESHOLD):
            if any(_same_position(price_pos, done) for done in handled):
                continue

            expected_icon = (price_pos[0] + PRICE_TO_ICON_OFFSET[0], price_pos[1] + PRICE_TO_ICON_OFFSET[1])
            gold_matches_near = [m for m in gold_icon_matches if _same_position(m, expected_icon)]
            gem_here = any(_same_position(m, expected_icon) for m in gem_icon_matches)

            if gold_matches_near and not gem_here:
                icon_x, icon_y = gold_matches_near[0]
                tap_x, tap_y = icon_x + ICON_CENTER_OFFSET, icon_y + ICON_CENTER_OFFSET
                return price, tap_x, tap_y, price_pos

            logger.info(f"Skipping a {price}-price slot: currency icon didn't confirm as gold-only.")
            handled.append(price_pos)  # don't re-consider this ambiguous slot again

    return None


def _confirm_or_cancel_popup(price, price_pos):
    """After tapping a slot, re-verify the confirmation popup itself is showing a
    gold icon (and no gem icon) before confirming. Cancels instead of guessing
    if that can't be confirmed -- this is the last line of defense against
    ever buying a gem-priced item."""
    ADBInterface.capture_screen(config.SCREENSHOT_PATH)

    gold_in_popup = _icons_in_popup(Detector.find_all(config.SCREENSHOT_PATH, GOLD_ICON_TEMPLATE, POPUP_ICON_THRESHOLD))
    gem_in_popup = _icons_in_popup(Detector.find_all(config.SCREENSHOT_PATH, GEM_ICON_TEMPLATE, POPUP_ICON_THRESHOLD))

    if gem_in_popup or not gold_in_popup:
        logger.error(f"Popup safety check failed for a {price}-gold slot (gold_in_popup={bool(gold_in_popup)}, gem_in_popup={bool(gem_in_popup)}) -- cancelling, not buying.")
        _close_popup_if_open()
        return False

    icon_x, icon_y = gold_in_popup[0]
    ADBInterface.tap(icon_x + ICON_CENTER_OFFSET, icon_y + ICON_CENTER_OFFSET)
    time.sleep(CLAIM_CONFIRM_DELAY_SECONDS)

    # A successful purchase can show a follow-up reward popup (its own close-X,
    # same style as the confirm popup's) before returning to the grid -- dismiss
    # whatever's on top rather than reading its mere presence as "still failed".
    _close_popup_if_open()

    badge_matches = Detector.find_all(config.SCREENSHOT_PATH, PURCHASED_BADGE_TEMPLATE, config.THRESHOLD)
    if not any(_same_position(m, price_pos, tolerance=SLOT_TOLERANCE_PX) for m in badge_matches):
        logger.error(f"Tapped to confirm the {price}-gold purchase but couldn't find a 'Purchased!' badge on that slot; treating as failed.")
        return False

    return True


def buy_gold_daily_deals():
    """Buy every Daily Deals slot confirmed to be gold-priced (never gem-priced)
    at or under config.MAX_GOLD_PRICE. Returns the list of prices successfully
    bought."""
    if not go_to_daily_deals():
        return []

    bought = []
    handled = []  # price-text positions already bought, or skipped as ambiguous

    for _ in range(MAX_SLOTS):
        ADBInterface.capture_screen(config.SCREENSHOT_PATH)
        found = _find_next_gold_slot(handled)
        if not found:
            break

        price, tap_x, tap_y, price_pos = found
        handled.append(price_pos)

        logger.info(f"Buying a {price}-gold Daily Deals slot...")
        ADBInterface.tap(tap_x, tap_y)
        time.sleep(CLAIM_CONFIRM_DELAY_SECONDS)

        if _confirm_or_cancel_popup(price, price_pos):
            logger.info(f"[V] Bought a {price}-gold Daily Deals slot.")
            bought.append(price)

    if bought:
        items_list = ", ".join(f"{p} gold" for p in bought)
        send_discord_message(f"Bought {len(bought)} Daily Deals item(s): {items_list}")

    return bought
