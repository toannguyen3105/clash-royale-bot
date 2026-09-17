"""Shared numeric constants (wait times, Android keycodes, timeouts).

Centralized here instead of as bare literals scattered across call sites, so each
value's meaning and reasoning is documented once instead of duplicated/guessed at
every usage. Most of the *_SECONDS values were tuned empirically while testing
against a real device — if a step starts flaking (e.g. a screen transition not
finishing in time), increase the relevant constant here rather than the call site.
"""

# --- Android keycodes (adb shell input keyevent <code>) ---

KEYCODE_POWER = "26"  # Toggles the screen on/off.
KEYCODE_ENTER = "66"  # Confirms a typed PIN on the lock screen.

# --- core/adb.py: unlock_device() / launch_app() timing ---

# Time for the screen to turn on after the power keyevent before the next ADB command.
POST_POWER_BUTTON_DELAY_SECONDS = 1

# Time for the unlock swipe gesture's animation to finish.
POST_SWIPE_DELAY_SECONDS = 1

# Time for the typed PIN + Enter keypress to register and dismiss the lock screen.
POST_PIN_ENTRY_DELAY_SECONDS = 1

# Clash Royale's observed cold-start load time on the test device; nothing useful
# can be checked on screen before this elapses.
GAME_LOAD_WAIT_SECONDS = 20

# --- tasks/navigation.py: ensure_at_lobby() timing ---

# Time for the screen transition after tapping the Battle nav icon to settle
# before capturing a screenshot to re-check for the Lobby.
LOBBY_NAV_SETTLE_SECONDS = 2

# --- tasks/daily_deals.py: claim_free_daily_card() timing ---

# Time for the Shop screen's sub-tab switch animation to settle after tapping
# the Shop nav icon, before capturing a screenshot to check for Daily Deals.
SHOP_NAV_SETTLE_SECONDS = 1.5

# Time for the "claimed" animation to finish playing after tapping the free
# card slot, before capturing a screenshot to confirm the claim.
CLAIM_CONFIRM_DELAY_SECONDS = 1.5

# --- utils/discord.py: send_discord_message() timing ---

# Max time to wait for the Discord webhook request before giving up.
DISCORD_REQUEST_TIMEOUT_SECONDS = 10

# --- tasks/donate_cards.py: donate_all_requested_cards() timing ---

# Time for the Chat screen's sub-tab switch animation to settle after tapping
# the Social nav icon, before capturing a screenshot to check for the Chat feed.
CHAT_NAV_SETTLE_SECONDS = 1.5

# Time for a single Donate tap's reward animation (+gold popup, progress bar
# update) to finish before capturing a screenshot to re-check the request.
DONATE_TAP_SETTLE_SECONDS = 1.2

# Time for the feed-scroll swipe's animation to finish before re-scanning for
# more donate requests.
SCROLL_SETTLE_SECONDS = 1
