from config import config
from core.adb import ADBInterface
from utils.logger import logger
from tasks.navigation import ensure_at_lobby
from tasks.daily_deals import claim_free_daily_card

def main():
    """Bot orchestration: Launch and verify login."""
    logger.info("--- Clash Royale Bot Starting ---")

    # 0. Ensure a device is connected before doing anything else
    if not ADBInterface.is_device_connected():
        return

    # 0.1. Ensure the game is actually installed on the device
    if not ADBInterface.is_app_installed(config.PACKAGE_NAME):
        return

    # 1. Launch the game
    # This also handles device unlocking
    ADBInterface.launch_app(config.PACKAGE_NAME)

    # 2. Verify target screen (Lobby), backing out of other screens if needed
    if not ensure_at_lobby():
        logger.error("[X] FAILED: Could not confirm Lobby status. Check screen or .env configuration.")
        return

    logger.info("[V] SUCCESS: Bot is confirmed at the Lobby screen.")

    # 3. Claim the free Daily Deals card, if available
    claim_free_daily_card()

if __name__ == "__main__":
    main()
