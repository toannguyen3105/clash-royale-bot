from config import config
from core.adb import ADBInterface
from vision.detector import Detector
from utils.logger import logger

def main():
    """Bot orchestration: Launch and verify login."""
    logger.info("--- Clash Royale Bot Starting ---")
    
    # 1. Launch the game
    # This also handles device unlocking
    ADBInterface.launch_app(config.PACKAGE_NAME)
    
    # 2. Capture a fresh screenshot
    ADBInterface.capture_screen(config.SCREENSHOT_PATH)
    
    # 3. Verify target screen (Lobby)
    if Detector.is_present(config.SCREENSHOT_PATH, config.TEMPLATE_PATH, config.THRESHOLD):
        logger.info("[V] SUCCESS: Bot is confirmed at the Lobby screen.")
    else:
        logger.error("[X] FAILED: Could not confirm Lobby status. Check screen or .env configuration.")

if __name__ == "__main__":
    main()
