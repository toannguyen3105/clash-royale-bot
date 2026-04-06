import pytest
from unittest.mock import patch, MagicMock
from core.adb import ADBInterface

@pytest.fixture
def mock_subprocess():
    with patch("subprocess.run") as mock:
        yield mock

@pytest.fixture
def mock_sleep():
    with patch("time.sleep") as mock:
        yield mock

@pytest.fixture
def mock_os():
    with patch("os.makedirs") as mock:
        yield mock

def test_unlock_device_screen_off(mock_subprocess, mock_sleep):
    """Test unlock_device when screen is OFF."""
    # Mock 'dumpsys display' output to indicate screen is OFF
    mock_subprocess.return_value = MagicMock(stdout="mScreenState=OFF", text=True)
    
    ADBInterface.unlock_device()
    
    # Verify Power button (26) was pressed
    # Verify Swipe was executed
    calls = [call[0][0] for call in mock_subprocess.call_args_list]
    
    assert any("keyevent" in cmd and "26" in cmd for cmd in calls)
    assert any("swipe" in cmd for cmd in calls)

def test_unlock_device_screen_on(mock_subprocess, mock_sleep):
    """Test unlock_device when screen is already ON."""
    # Mock 'dumpsys display' output to indicate screen is ON
    mock_subprocess.return_value = MagicMock(stdout="mScreenState=ON", text=True)
    
    ADBInterface.unlock_device()
    
    # Verify Power button (26) was NOT pressed
    # Verify Swipe was still executed
    calls = [call[0][0] for call in mock_subprocess.call_args_list]
    
    assert not any("keyevent" in cmd and "26" in cmd for cmd in calls)
    assert any("swipe" in cmd for cmd in calls)

def test_launch_app(mock_subprocess, mock_sleep):
    """Test launch_app calls unlock and monkey command."""
    with patch.object(ADBInterface, 'unlock_device') as mock_unlock:
        ADBInterface.launch_app("com.test.app")
        
        mock_unlock.assert_called_once()
        # Verify monkey command
        calls = [call[0][0] for call in mock_subprocess.call_args_list]
        assert any("monkey" in cmd and "com.test.app" in cmd for cmd in calls)

def test_capture_screen(mock_subprocess, mock_os):
    """Test capture_screen creates dir and runs screencap."""
    ADBInterface.capture_screen("path/to/screen.png")
    
    mock_os.assert_called_once_with("path/to", exist_ok=True)
    # Verify screencap command
    # Note: subprocess.run is called with shell=True for this specific command
    mock_subprocess.assert_called_with("adb exec-out screencap -p > path/to/screen.png", shell=True)

def test_tap(mock_subprocess):
    """Test tap calls input tap with correct coords."""
    ADBInterface.tap(100, 200)
    
    mock_subprocess.assert_called_with(["adb", "shell", "input", "tap", "100", "200"])
