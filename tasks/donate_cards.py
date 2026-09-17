import time
from core.adb import ADBInterface
from vision.detector import Detector
from utils.logger import logger
from utils.discord import send_discord_message
from config import config
from constants import CHAT_NAV_SETTLE_SECONDS, DONATE_TAP_SETTLE_SECONDS, SCROLL_SETTLE_SECONDS

# Pixel coordinates below are tied to the current device's resolution (1080x2400),
# same constraint as the templates in assets/templates/.
SOCIAL_NAV_ICON = (758, 2340)
MAX_CHAT_NAV_ATTEMPTS = 3

# Offset from the top-left of a matched "Requesting Cards!" banner to the
# center of that request's Donate button, measured on the current layout.
DONATE_BUTTON_OFFSET = (690, 145)

# Offset from the same banner's top-left to where the disabled-Donate-button
# template is expected to match, if that request has hit today's donation cap.
DONATE_DISABLED_OFFSET = (590, 104)

# The disabled (grayed-out) Donate button template scores ~0.86 against the
# active (green) Donate button too -- both are the same shape/text, just a
# different color -- so this check needs a much stricter threshold than the
# usual config.THRESHOLD (0.8) to tell them apart. Verified live: exact match
# on the true disabled button scores 1.0, green buttons score ~0.86.
DONATE_DISABLED_THRESHOLD = 0.95

# Swipe gesture used to scroll the feed down (reveal further/older requests).
SCROLL_FROM = (540, 2000)
SCROLL_TO = (540, 700)
MAX_SCROLL_ATTEMPTS = 5

# Safety cap: give up on a single request after this many taps if neither the
# banner disappearing nor the disabled-button check has ended it -- a last
# resort in case some other, still-unseen state isn't handled above.
MAX_TAPS_PER_REQUEST = 60

# How close (in pixels) a re-detected banner's top-left has to be to a previous
# one to count as "the same request" rather than a different one.
SAME_REQUEST_TOLERANCE_PX = 20

REQUESTING_CARDS_TEMPLATE = "assets/templates/requesting_cards_banner.png"
CHAT_SCREEN_TEMPLATE = "assets/templates/chat_friendly_battle_button.png"
DONATE_DISABLED_TEMPLATE = "assets/templates/donate_button_disabled.png"
CHAT_OK_BUTTON_TEMPLATE = "assets/templates/chat_ok_button.png"

# The "New Messages" feed is a modal overlay: while it's showing, the bottom nav
# bar underneath (Shop/Battle/Social/...) doesn't receive taps at all, which
# stranded the bot on a previous run. Must be dismissed before returning.
CHAT_OK_BUTTON = (540, 2330)


def _go_to_chat():
    """Tap the Social nav icon until the Chat feed is detected (nav icons remember
    the last-viewed sub-tab, so a single tap doesn't reliably land there)."""
    for attempt in range(1, MAX_CHAT_NAV_ATTEMPTS + 1):
        ADBInterface.tap(*SOCIAL_NAV_ICON)
        time.sleep(CHAT_NAV_SETTLE_SECONDS)
        ADBInterface.capture_screen(config.SCREENSHOT_PATH)
        if Detector.is_present(config.SCREENSHOT_PATH, CHAT_SCREEN_TEMPLATE, config.THRESHOLD):
            return True
        logger.info(f"Chat feed not found yet (attempt {attempt}/{MAX_CHAT_NAV_ATTEMPTS}).")

    logger.error("Could not navigate to the Chat feed.")
    return False


def _same_position(a, b):
    return abs(a[0] - b[0]) < SAME_REQUEST_TOLERANCE_PX and abs(a[1] - b[1]) < SAME_REQUEST_TOLERANCE_PX


def _topmost_request(given_up):
    """Return the (x, y) top-left of the topmost visible 'Requesting Cards!' banner
    that isn't in `given_up`, or None."""
    matches = Detector.find_all(config.SCREENSHOT_PATH, REQUESTING_CARDS_TEMPLATE, config.THRESHOLD)
    for match in matches:
        if not any(_same_position(match, done) for done in given_up):
            return match
    return None


def _donate_button_disabled(anchor):
    """Check whether the request at `anchor` has hit its donation cap (grayed-out button)."""
    expected = (anchor[0] + DONATE_DISABLED_OFFSET[0], anchor[1] + DONATE_DISABLED_OFFSET[1])
    matches = Detector.find_all(config.SCREENSHOT_PATH, DONATE_DISABLED_TEMPLATE, DONATE_DISABLED_THRESHOLD)
    return any(_same_position(m, expected) for m in matches)


def _dismiss_new_messages_modal():
    """Close the New Messages modal (OK button) if still showing, so the bottom
    nav bar it covers is tappable again for whatever runs next."""
    ADBInterface.capture_screen(config.SCREENSHOT_PATH)
    if Detector.is_present(config.SCREENSHOT_PATH, CHAT_OK_BUTTON_TEMPLATE, config.THRESHOLD):
        logger.info("Dismissing the New Messages modal...")
        ADBInterface.tap(*CHAT_OK_BUTTON)
        time.sleep(CHAT_NAV_SETTLE_SECONDS)


def donate_all_requested_cards():
    """Donate to every pending clanmate card request visible in the Chat feed,
    scrolling for more. Each request is tapped repeatedly until it either
    completes (disappears from the feed), hits its donation cap (Donate button
    grays out), or hits the per-request safety cap -- any of which moves on to
    the next request rather than stopping the whole run.
    Returns the number of successful donate taps made."""
    if not _go_to_chat():
        return 0

    donated_count = 0
    scroll_attempts = 0
    given_up = []

    while True:
        ADBInterface.capture_screen(config.SCREENSHOT_PATH)
        anchor = _topmost_request(given_up)

        if anchor is None:
            if scroll_attempts >= MAX_SCROLL_ATTEMPTS:
                break
            logger.info(f"No more donatable requests visible, scrolling for more (attempt {scroll_attempts + 1}/{MAX_SCROLL_ATTEMPTS})...")
            ADBInterface.swipe(*SCROLL_FROM, *SCROLL_TO)
            time.sleep(SCROLL_SETTLE_SECONDS)
            scroll_attempts += 1
            continue

        scroll_attempts = 0  # found a request, reset the "give up scrolling" counter
        donate_x = anchor[0] + DONATE_BUTTON_OFFSET[0]
        donate_y = anchor[1] + DONATE_BUTTON_OFFSET[1]

        for tap_attempt in range(1, MAX_TAPS_PER_REQUEST + 1):
            ADBInterface.tap(donate_x, donate_y)
            time.sleep(DONATE_TAP_SETTLE_SECONDS)
            ADBInterface.capture_screen(config.SCREENSHOT_PATH)
            donated_count += 1

            if _donate_button_disabled(anchor):
                logger.info("Donate button is now disabled (today's donation cap for this card), moving to the next request.")
                given_up.append(anchor)
                break

            still_there = any(_same_position(m, anchor) for m in Detector.find_all(config.SCREENSHOT_PATH, REQUESTING_CARDS_TEMPLATE, config.THRESHOLD))
            if not still_there:
                break
        else:
            logger.error(f"Hit the safety cap ({MAX_TAPS_PER_REQUEST} taps) on one request without a clear end state; moving to the next request.")
            given_up.append(anchor)

    logger.info(f"Donation run complete: {donated_count} donate tap(s) made.")
    if donated_count:
        send_discord_message(f"Donated cards to clanmates: {donated_count} donate action(s) made.")

    _dismiss_new_messages_modal()
    return donated_count
