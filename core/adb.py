import subprocess
import time
import os
from utils.logger import logger
from config import config

class ADBInterface:
    """Handles all interaction with the Android device via ADB."""
    
    @staticmethod
    def unlock_device():
        logger.info("Checking screen state...")
        res = subprocess.run(["adb", "shell", "dumpsys", "display"], capture_output=True, text=True)
        if "mScreenState=OFF" in res.stdout or "state=OFF" in res.stdout:
            logger.info("Screen is OFF. Pressing Power button...")
            subprocess.run(["adb", "shell", "input", "keyevent", "26"])
        
        logger.info("Swiping up to unlock...")
        subprocess.run(["adb", "shell", "input", "swipe", "500", "2000", "500", "500"])
        time.sleep(1)

    @staticmethod
    def launch_app(package_name):
        ADBInterface.unlock_device()
        logger.info(f"Starting {package_name}...")
        subprocess.run(["adb", "shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"], capture_output=True)
        logger.info("Waiting for game to load (20 seconds)...")
        time.sleep(20)

    @staticmethod
    def capture_screen(output_path):
        logger.info(f"Capturing screenshot to {output_path}...")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        subprocess.run(f"adb exec-out screencap -p > {output_path}", shell=True)

    @staticmethod
    def tap(x, y):
        logger.info(f"Tapping at ({x}, {y})")
        subprocess.run(["adb", "shell", "input", "tap", str(x), str(y)])
