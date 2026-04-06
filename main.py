import cv2
import numpy as np
import os
import subprocess
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
PACKAGE_NAME = os.getenv("PACKAGE_NAME", "com.supercell.clashroyale")
TEMPLATE_PATH = os.getenv("TEMPLATE_PATH", "assets/templates/battle_button.png")
SCREENSHOT_PATH = os.getenv("SCREENSHOT_PATH", "assets/debug/screen.png")
THRESHOLD = float(os.getenv("THRESHOLD", 0.8))

def unlock_device():
    print("[+] Checking screen state...")
    # Check if the screen is OFF
    res = subprocess.run(["adb", "shell", "dumpsys", "display"], capture_output=True, text=True)
    if "mScreenState=OFF" in res.stdout or "state=OFF" in res.stdout:
        print("[*] Screen is OFF. Pressing Power button...")
        subprocess.run(["adb", "shell", "input", "keyevent", "26"]) # Power button
    
    # Swipe up to unlock (assumes no password or just swipe-to-unlock)
    print("[*] Swiping up to unlock...")
    subprocess.run(["adb", "shell", "input", "swipe", "500", "2000", "500", "500"])
    time.sleep(1)

def launch_game():
    unlock_device()
    print(f"[+] Starting {PACKAGE_NAME}...")
    subprocess.run(["adb", "shell", "monkey", "-p", PACKAGE_NAME, "-c", "android.intent.category.LAUNCHER", "1"], capture_output=True)
    print("[*] Waiting for game to load (20 seconds)...")
    time.sleep(20)  # Increase wait time for Clash Royale to fully load

def capture_screen():
    print("[+] Capturing screenshot...")
    os.makedirs(os.path.dirname(SCREENSHOT_PATH), exist_ok=True)
    subprocess.run(f"adb exec-out screencap -p > {SCREENSHOT_PATH}", shell=True)

def check_login():
    if not os.path.exists(TEMPLATE_PATH):
        print(f"[-] Error: Template file not found at {TEMPLATE_PATH}")
        return False

    # Load screen and template
    screen = cv2.imread(SCREENSHOT_PATH)
    template = cv2.imread(TEMPLATE_PATH)

    if screen is None or template is None:
        print("[-] Error: Could not read images.")
        return False

    # Template Matching
    res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

    print(f"[*] Max match value: {max_val:.2f}")

    if max_val >= THRESHOLD:
        print("[V] CONFIRMED: You are logged in and at the Lobby.")
        return True
    else:
        print("[X] WARNING: 'Battle' button not found. You might not be logged in or at a different screen.")
        return False

def main():
    """Simple bot execution: Launch and check login."""
    print("--- Clash Royale Login Check ---")
    
    launch_game()
    capture_screen()
    
    if check_login():
        print("[V] SUCCESS: Game is logged in and at the Lobby.")
    else:
        print("[X] FAILED: Could not confirm login status. Check your screen.")

if __name__ == "__main__":
    main()
