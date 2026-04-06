import os
import pytest
import subprocess
from dotenv import load_dotenv

# Load configuration for tests
load_dotenv()

def test_python_libraries():
    """Verify that required Python libraries are installed."""
    try:
        import cv2
        import numpy
        import dotenv
        print("\n[V] Python libraries (cv2, numpy, dotenv) are ready.")
    except ImportError as e:
        pytest.fail(f"Missing Python library: {e}. Please run 'make setup'.")

def test_required_assets():
    """Verify the existence of required template files from .env."""
    battle_button_path = os.getenv("TEMPLATE_PATH", "assets/templates/battle_button.png")
    
    required_files = [
        battle_button_path,
    ]
    for file_path in required_files:
        assert os.path.exists(file_path), f"Missing critical file: {file_path}"
    print("\n[V] All required assets are present.")

def test_adb_installed():
    """Verify that ADB tool is installed in the system."""
    try:
        result = subprocess.run(["adb", "--version"], capture_output=True, text=True)
        assert result.returncode == 0, "ADB command is not working."
        print(f"\n[V] ADB is installed: {result.stdout.splitlines()[0]}")
    except FileNotFoundError:
        pytest.fail("ADB command not found. Please install Android SDK Platform Tools.")
