# Biến số
VENV = venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

.PHONY: setup run screenshot test clean

# 1. Environment Setup
setup:
	@echo "[+] Installing system tools (adb, scrcpy)..."
	sudo apt update && sudo apt install -y adb scrcpy
	@echo "[+] Creating Python virtual environment (venv)..."
	python3 -m venv $(VENV)
	@echo "[+] Installing Python libraries..."
	$(PIP) install -r requirements.txt
	$(PIP) install pytest
	@echo "[V] Setup complete!"

# 2. Run Bot
run:
	@echo "[+] Starting bot..."
	$(PYTHON) main.py

# 3. Environment Check (Test)
test:
	@echo "[+] Running system checks..."
	$(VENV)/bin/pytest -v tests/

# 4. Manual Screenshot (for template creation)
screenshot:
	@echo "[+] Capturing phone screenshot..."
	adb exec-out screencap -p > screen.png
	@echo "[V] Saved to screen.png"

# 5. Cleanup
clean:
	@echo "[+] Cleaning up..."
	rm -rf $(VENV)
	rm -f screen.png
	@echo "[V] Cleanup complete!"
