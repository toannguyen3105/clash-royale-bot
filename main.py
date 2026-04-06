import cv2
import numpy as np
import os
import subprocess
import time

# Configuration
PACKAGE_NAME = "com.supercell.clashroyale"
TEMPLATE_PATH = "assets/templates/battle_button.png"
SCREENSHOT_PATH = "screen.png"
THRESHOLD = 0.8  # Minimum accuracy threshold

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

if __name__ == "__main__":
    # 1. Launch the game
    launch_game()
    
    # 2. Capture the screen
    capture_screen()
    
    # 3. Check status
    check_login()
