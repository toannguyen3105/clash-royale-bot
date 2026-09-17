import subprocess
import time
import os
import re
from utils.logger import logger
from config import config
from constants import (
    KEYCODE_POWER,
    KEYCODE_ENTER,
    POST_POWER_BUTTON_DELAY_SECONDS,
    POST_SWIPE_DELAY_SECONDS,
    POST_PIN_ENTRY_DELAY_SECONDS,
    GAME_LOAD_WAIT_SECONDS,
)

class ADBInterface:
    """Handles all interaction with the Android device via ADB."""

    @staticmethod
    def _base_cmd():
        """Build the base 'adb' command, targeting config.DEVICE_SERIAL when set."""
        if config.DEVICE_SERIAL:
            return ["adb", "-s", config.DEVICE_SERIAL]
        return ["adb"]

    @staticmethod
    def is_device_connected():
        """Check that ADB is installed and exactly one device is connected, authorized,
        and unambiguously selected (via DEVICE_SERIAL if multiple devices are present)."""
        try:
            res = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        except FileNotFoundError:
            logger.error("ADB not found in PATH. Please install ADB (see 'make setup').")
            return False

        lines = res.stdout.strip().splitlines()[1:]
        devices = [line.split()[0] for line in lines if line.strip() and line.split()[-1] == "device"]

        if not devices:
            logger.error("No authorized ADB device connected. Run 'adb devices' and ensure USB debugging is enabled and authorized on the phone.")
            return False

        if config.DEVICE_SERIAL:
            if config.DEVICE_SERIAL not in devices:
                logger.error(f"Configured DEVICE_SERIAL '{config.DEVICE_SERIAL}' not found among connected devices: {devices}")
                return False
            return True

        if len(devices) > 1:
            logger.error(f"Multiple ADB devices connected ({devices}) but DEVICE_SERIAL is not set in .env. Set DEVICE_SERIAL to one of these to select which device to control.")
            return False

        return True

    @staticmethod
    def is_app_installed(package_name):
        """Check whether the given package is installed on the connected device."""
        res = subprocess.run(ADBInterface._base_cmd() + ["shell", "pm", "list", "packages", package_name], capture_output=True, text=True)
        installed = any(line.strip() == f"package:{package_name}" for line in res.stdout.splitlines())
        if not installed:
            play_store_url = f"https://play.google.com/store/apps/details?id={package_name}"
            logger.error(f"App '{package_name}' is not installed on the device. Install it first: {play_store_url}")
        return installed

    @staticmethod
    def is_device_locked():
        """Check the keyguard/trust state. Defaults to True (locked) if the state can't be determined,
        so the bot falls back to always running the full unlock flow rather than skipping it wrongly."""
        res = subprocess.run(ADBInterface._base_cmd() + ["shell", "dumpsys", "trust"], capture_output=True, text=True)
        match = re.search(r"deviceLocked=(\d)", res.stdout)
        if not match:
            return True
        return match.group(1) == "1"

    @staticmethod
    def is_app_in_foreground(package_name):
        """Check whether the given package is the currently focused app."""
        res = subprocess.run(ADBInterface._base_cmd() + ["shell", "dumpsys", "window"], capture_output=True, text=True)
        for line in res.stdout.splitlines():
            if "mFocusedApp" in line and package_name in line:
                return True
        return False

    @staticmethod
    def unlock_device():
        logger.info("Checking screen state...")
        res = subprocess.run(ADBInterface._base_cmd() + ["shell", "dumpsys", "display"], capture_output=True, text=True)
        if "mScreenState=OFF" in res.stdout or "state=OFF" in res.stdout:
            logger.info("Screen is OFF. Pressing Power button...")
            subprocess.run(ADBInterface._base_cmd() + ["shell", "input", "keyevent", KEYCODE_POWER])
            time.sleep(POST_POWER_BUTTON_DELAY_SECONDS)

        if not ADBInterface.is_device_locked():
            logger.info("Device is already unlocked, skipping swipe/PIN.")
            return

        logger.info("Swiping up to unlock...")
        subprocess.run(ADBInterface._base_cmd() + ["shell", "input", "swipe", "500", "2000", "500", "500"])
        time.sleep(POST_SWIPE_DELAY_SECONDS)

        if config.DEVICE_PIN:
            logger.info("Entering PIN to unlock...")
            subprocess.run(ADBInterface._base_cmd() + ["shell", "input", "text", config.DEVICE_PIN])
            subprocess.run(ADBInterface._base_cmd() + ["shell", "input", "keyevent", KEYCODE_ENTER])
            time.sleep(POST_PIN_ENTRY_DELAY_SECONDS)

    @staticmethod
    def launch_app(package_name):
        ADBInterface.unlock_device()

        if ADBInterface.is_app_in_foreground(package_name):
            logger.info(f"{package_name} is already in the foreground, skipping launch.")
            return

        logger.info(f"Starting {package_name}...")
        subprocess.run(ADBInterface._base_cmd() + ["shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"], capture_output=True)
        logger.info(f"Waiting for game to load ({GAME_LOAD_WAIT_SECONDS} seconds)...")
        time.sleep(GAME_LOAD_WAIT_SECONDS)

    @staticmethod
    def capture_screen(output_path):
        logger.info(f"Capturing screenshot to {output_path}...")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        result = subprocess.run(ADBInterface._base_cmd() + ["exec-out", "screencap", "-p"], capture_output=True)
        with open(output_path, "wb") as f:
            f.write(result.stdout)

    @staticmethod
    def tap(x, y):
        logger.info(f"Tapping at ({x}, {y})")
        subprocess.run(ADBInterface._base_cmd() + ["shell", "input", "tap", str(x), str(y)])

    @staticmethod
    def swipe(x1, y1, x2, y2, duration_ms=300):
        logger.info(f"Swiping from ({x1}, {y1}) to ({x2}, {y2})")
        subprocess.run(ADBInterface._base_cmd() + ["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)])
