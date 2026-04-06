# Variables
VENV = venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip
ADB = adb
SCREENSHOT_DIR = assets/debug
SCREENSHOT_FILE = $(SCREENSHOT_DIR)/screen.png
TEST_DIR = tests/

.PHONY: setup run screenshot test clean

# 1. Environment Setup
setup:
	@echo "[+] Checking for system tools (adb, scrcpy)..."
	@which $(ADB) > /dev/null || (echo "[!] Installing adb, scrcpy..." && sudo apt update && sudo apt install -y adb scrcpy)
	@echo "[+] Creating Python virtual environment..."
	@[ -d $(VENV) ] || python3 -m venv $(VENV)
	@echo "[+] Installing dependencies..."
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements.txt
	@echo "[V] Setup complete!"

# 2. Run Bot
run:
	@echo "[+] Starting Clash Royale Bot..."
	@$(PYTHON) main.py

# 3. Environment Check
test:
	@echo "[+] Running environment verification tests..."
	@$(PYTHON) -m pytest -v $(TEST_DIR)

# 4. Manual Screenshot
screenshot:
	@echo "[+] Capturing device screenshot..."
	@mkdir -p $(SCREENSHOT_DIR)
	@$(ADB) exec-out screencap -p > $(SCREENSHOT_FILE)
	@echo "[V] Image saved to $(SCREENSHOT_FILE)"

# 5. Cleanup
clean:
	@echo "[+] Cleaning temporary files and environment..."
	rm -rf $(VENV)
	rm -rf $(SCREENSHOT_DIR)
	rm -rf __pycache__ $(TEST_DIR)__pycache__
	@echo "[V] Cleanup complete!"
