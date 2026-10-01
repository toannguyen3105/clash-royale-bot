import argparse
import random
import sys
import time
from datetime import datetime
from config import config
from constants import DEFAULT_DONATE_JITTER_MINUTES
from core.adb import ADBInterface
from utils.logger import logger
from utils.discord import send_discord_message
from utils.run_lock import single_run_lock
from utils import state
from utils import history
from utils.app_home import save_failure_screenshot
from tasks.navigation import ensure_at_lobby
from tasks.daily_deals import claim_free_daily_card
from tasks.buy_gold_deals import buy_gold_daily_deals
from tasks.donate_cards import donate_all_requested_cards

# Keys in the state file for tasks that only need to succeed once per game day.
FREE_CARD_TASK = "free_card"
GOLD_DEALS_TASK = "gold_deals"


def start_game(restart_app):
    """Get the game to the Lobby: check the device, unlock it, launch the game.
    Returns True on success."""
    # 0. Ensure a device is connected before doing anything else
    if not ADBInterface.is_device_connected():
        return False

    # 0.1. Ensure the game is actually installed on the device
    if not ADBInterface.is_app_installed(config.PACKAGE_NAME):
        return False

    # 1. Launch the game
    # This also handles device unlocking. Force-stopping first (if requested)
    # makes it cold-start at the Lobby rather than resume a previous run's screen.
    if restart_app:
        ADBInterface.force_stop_app(config.PACKAGE_NAME)
    ADBInterface.launch_app(config.PACKAGE_NAME)

    # 2. Verify target screen (Lobby), backing out of other screens if needed
    if not ensure_at_lobby():
        logger.error("[X] FAILED: Could not confirm Lobby status. Check screen or .env configuration.")
        saved = save_failure_screenshot(config.SCREENSHOT_PATH, "lobby")
        if saved:
            logger.info(f"Saved the screen at the time of failure to {saved}")
        return False

    logger.info("[V] SUCCESS: Bot is confirmed at the Lobby screen.")
    return True


def run_daily_tasks(record):
    """Claim the free Daily Deals card and buy gold-priced deals, each at most once
    per game day: a task already recorded as done today is skipped entirely, so
    this can safely run again (a retry, or by hand) later the same day.
    Each task's outcome is stored in `record`. Returns True if neither failed."""
    if state.is_done_today(FREE_CARD_TASK):
        logger.info("Free Daily Deals card already handled today, skipping.")
        record["free_card"] = "skipped"
    elif claim_free_daily_card():
        state.mark_done_today(FREE_CARD_TASK)
        record["free_card"] = "collected"
    else:
        record["free_card"] = "failed"

    if state.is_done_today(GOLD_DEALS_TASK):
        logger.info("Gold Daily Deals already handled today, skipping.")
        record["gold_deals"] = "skipped"
    else:
        bought = buy_gold_daily_deals()
        if bought is not None:
            # Marked done even if some slot was skipped or a purchase couldn't be
            # confirmed: re-attempting a purchase that just failed its safety checks
            # isn't worth the risk. The next game day starts fresh.
            state.mark_done_today(GOLD_DEALS_TASK)
            record["gold_deals"] = bought
        else:
            record["gold_deals"] = "failed"

    return "failed" not in (record["free_card"], record["gold_deals"])


def notify_daily_result(record, ok):
    """One Discord message per daily run that did something (a retry that found
    everything already done stays silent), so a missing message means the bot
    didn't run."""
    if record.get("free_card") == "skipped" and record.get("gold_deals") == "skipped":
        return
    icon = "✅" if ok else "⚠️"
    send_discord_message(f"{icon} Daily: {history.describe_run(record)}")


def run(command, record):
    """Run one bot command ("daily", "donate" or "all") end to end, storing outcomes
    in `record`. Returns True on success, False on failure."""
    # Donate runs often and doesn't care which screen the game resumes on (it
    # navigates to the chat itself), so it skips the extra ~20s cold start.
    restart_app = config.RESTART_APP_ON_START and command != "donate"

    try:
        started = start_game(restart_app)
        if not started and not restart_app:
            # The resumed game was stuck on some screen ensure_at_lobby() can't back
            # out of (e.g. a full-screen reward track with its own OK button). A cold
            # start always lands on the Lobby, so try once more from scratch.
            logger.info("Could not reach the Lobby from the resumed game, retrying with an app restart...")
            started = start_game(restart_app=True)
        if not started:
            record["error"] = "could not reach the Lobby"
            send_discord_message(f"❌ Bot run `{command}` failed: could not get the game to the Lobby.")
            return False

        ok = True
        if command in ("daily", "all"):
            ok = run_daily_tasks(record)
            notify_daily_result(record, ok)
        if command in ("donate", "all"):
            record["donations"] = donate_all_requested_cards()
        return ok
    finally:
        # Re-lock the phone instead of leaving it unlocked and unattended.
        if config.SCREEN_OFF_AFTER_RUN:
            ADBInterface.turn_screen_off()


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Clash Royale bot")
    parser.add_argument(
        "command", nargs="?", default="all", choices=["daily", "donate", "all"],
        help="daily: free card + gold deals (once per game day); donate: donate to clan requests; all: both (default)",
    )
    parser.add_argument(
        "--jitter-minutes", type=float, default=0,
        help=f"wait a random 0..N minutes before starting (scheduled donate runs use {DEFAULT_DONATE_JITTER_MINUTES})",
    )
    return parser.parse_args(argv)


def main(argv=None):
    """Bot entry point. Returns True on success, False on failure, so the process
    can exit with a non-zero code for launchd/cron monitoring."""
    args = parse_args(argv if argv is not None else [])
    logger.info(f"--- Clash Royale Bot Starting ({args.command}) ---")

    # Wait before taking the lock, so a sleeping run doesn't block others.
    if args.jitter_minutes > 0:
        delay = random.uniform(0, args.jitter_minutes * 60)
        logger.info(f"Waiting {delay / 60:.1f} min (random jitter) before starting...")
        time.sleep(delay)

    record = {"start": datetime.now().isoformat(timespec="seconds"), "command": args.command, "ok": False}
    try:
        with single_run_lock() as acquired:
            if not acquired:
                logger.warning("Another bot run is in progress, exiting without doing anything.")
                record["error"] = "skipped: another run in progress"
                return False
            record["ok"] = run(args.command, record)
            return record["ok"]
    except Exception as e:
        record["error"] = f"crashed: {type(e).__name__}: {e}"
        raise
    finally:
        # Every run leaves exactly one history line, whatever happened.
        record["end"] = datetime.now().isoformat(timespec="seconds")
        history.record_run(record)


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1:]) else 1)
