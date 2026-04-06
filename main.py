import cv2
import numpy as np
import os
import subprocess
import time

# Cấu hình
PACKAGE_NAME = "com.supercell.clashroyale"
TEMPLATE_PATH = "assets/templates/battle_button.png"
SCREENSHOT_PATH = "screen.png"
THRESHOLD = 0.8  # Độ chính xác tối thiểu (80%)

def unlock_device():
    print("[+] Đang kiểm tra trạng thái màn hình...")
    # Kiểm tra xem màn hình có đang tắt không
    res = subprocess.run(["adb", "shell", "dumpsys", "display"], capture_output=True, text=True)
    if "mScreenState=OFF" in res.stdout or "state=OFF" in res.stdout:
        print("[*] Màn hình đang tắt. Đang bật nguồn...")
        subprocess.run(["adb", "shell", "input", "keyevent", "26"]) # Nút Nguồn
    
    # Vuốt lên để mở khóa (giả định không có mật khẩu hoặc chỉ là vuốt để mở)
    print("[*] Đang vuốt để mở khóa...")
    subprocess.run(["adb", "shell", "input", "swipe", "500", "2000", "500", "500"])
    time.sleep(1)

def launch_game():
    unlock_device()
    print(f"[+] Đang khởi động {PACKAGE_NAME}...")
    subprocess.run(["adb", "shell", "monkey", "-p", PACKAGE_NAME, "-c", "android.intent.category.LAUNCHER", "1"], capture_output=True)
    print("[*] Đang đợi game load (20 giây)...")
    time.sleep(20)  # Tăng thời gian chờ lên 20s cho chắc chắn

def capture_screen():
    print("[+] Đang chụp ảnh màn hình...")
    # Dùng adb exec-out để lấy ảnh trực tiếp vào Python hoặc lưu tạm ra file
    subprocess.run(f"adb exec-out screencap -p > {SCREENSHOT_PATH}", shell=True)

def check_login():
    if not os.path.exists(TEMPLATE_PATH):
        print(f"[-] Lỗi: Không tìm thấy file mẫu tại {TEMPLATE_PATH}")
        return False

    # Đọc ảnh màn hình và ảnh mẫu
    screen = cv2.imread(SCREENSHOT_PATH)
    template = cv2.imread(TEMPLATE_PATH)

    if screen is None or template is None:
        print("[-] Lỗi: Không thể đọc ảnh.")
        return False

    # So khớp mẫu (Template Matching)
    res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

    print(f"[*] Độ khớp tối đa: {max_val:.2f}")

    if max_val >= THRESHOLD:
        print("[V] XÁC NHẬN: Bạn đã đăng nhập và đang ở màn hình chính (Lobby).")
        return True
    else:
        print("[X] CẢNH BÁO: Không tìm thấy nút 'Battle'. Có thể bạn chưa đăng nhập hoặc đang ở màn hình khác.")
        return False

if __name__ == "__main__":
    # 1. Mở game
    launch_game()
    
    # 2. Chụp ảnh
    capture_screen()
    
    # 3. Kiểm tra
    check_login()
