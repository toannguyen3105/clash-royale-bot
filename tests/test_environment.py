import os
import pytest
import subprocess
from config import config
from vision.detector import Detector

def test_python_libraries():
    """Verify that required Python libraries are installed."""
    try:
        import cv2
        import numpy
        import dotenv
        print("\n[V] Core Python libraries (cv2, numpy, dotenv) are ready.")
    except ImportError as e:
        pytest.fail(f"Missing Python library: {e}. Please run 'make setup'.")

def test_required_assets():
    """Verify the existence of required template files using the config module."""
    battle_button_path = config.TEMPLATE_PATH
    
    assert battle_button_path, "TEMPLATE_PATH is not defined in config."
    assert os.path.exists(battle_button_path), f"Missing critical asset: {battle_button_path}"
    print(f"\n[V] Configured asset found: {battle_button_path}")

def test_config_loading():
    """Verify that configuration is correctly loaded from .env or defaults."""
    assert config.PACKAGE_NAME is not None
    assert isinstance(config.THRESHOLD, float)
    print("\n[V] Configuration loaded successfully.")

def test_adb_installed():
    """Verify that ADB tool is installed in the system."""
    try:
        # We use a simple command to check adb availability
        result = subprocess.run(["adb", "--version"], capture_output=True, text=True)
        assert result.returncode == 0, "ADB command is not responding correctly."
        print(f"\n[V] ADB is active: {result.stdout.splitlines()[0]}")
    except FileNotFoundError:
        pytest.fail("ADB command not found in the system PATH.")
