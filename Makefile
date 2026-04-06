# Biến số
VENV = venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

.PHONY: setup run screenshot clean

# 1. Cài đặt môi trường
setup:
	@echo "[+] Đang cài đặt công cụ hệ thống (adb, scrcpy)..."
	sudo apt update && sudo apt install -y adb scrcpy
	@echo "[+] Đang tạo môi trường ảo Python (venv)..."
	python3 -m venv $(VENV)
	@echo "[+] Đang cài đặt các thư viện Python..."
	$(PIP) install -r requirements.txt
	@echo "[V] Đã thiết lập xong!"

# 2. Chạy bot
run:
	@echo "[+] Đang khởi động bot..."
	$(PYTHON) main.py

# 3. Chụp ảnh màn hình thủ công (để lấy mẫu)
screenshot:
	@echo "[+] Đang chụp ảnh màn hình điện thoại..."
	adb exec-out screencap -p > screen.png
	@echo "[V] Đã lưu vào screen.png"

# 4. Dọn dẹp
clean:
	@echo "[+] Đang dọn dẹp..."
	rm -rf $(VENV)
	rm -f screen.png
	@echo "[V] Đã dọn sạch!"
