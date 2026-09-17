import pytest
from unittest.mock import patch, MagicMock
from core.adb import ADBInterface
from config import config

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

@pytest.fixture(autouse=True)
def reset_device_serial():
    """Ensure tests are deterministic regardless of the developer's local .env."""
    with patch.object(config, "DEVICE_SERIAL", ""):
        yield

@pytest.fixture(autouse=True)
def reset_device_pin():
    """Ensure tests are deterministic regardless of the developer's local .env."""
    with patch.object(config, "DEVICE_PIN", ""):
        yield

def test_is_device_connected_no_devices(mock_subprocess):
    """Test is_device_connected when no devices are listed."""
    mock_subprocess.return_value = MagicMock(stdout="List of devices attached\n")

    assert ADBInterface.is_device_connected() is False

def test_is_device_connected_unauthorized(mock_subprocess):
    """Test is_device_connected when the only device is unauthorized."""
    mock_subprocess.return_value = MagicMock(stdout="List of devices attached\n622caf39\tunauthorized\n")

    assert ADBInterface.is_device_connected() is False

def test_is_device_connected_ok(mock_subprocess):
    """Test is_device_connected when a device is connected and authorized."""
    mock_subprocess.return_value = MagicMock(stdout="List of devices attached\n622caf39\tdevice\n")

    assert ADBInterface.is_device_connected() is True

def test_is_device_connected_adb_not_found(mock_subprocess):
    """Test is_device_connected when the adb binary is not installed."""
    mock_subprocess.side_effect = FileNotFoundError()

    assert ADBInterface.is_device_connected() is False

def test_is_device_connected_multiple_no_serial(mock_subprocess):
    """Test is_device_connected when multiple devices are connected and DEVICE_SERIAL is unset."""
    mock_subprocess.return_value = MagicMock(stdout="List of devices attached\nAAA\tdevice\nBBB\tdevice\n")

    with patch.object(config, "DEVICE_SERIAL", ""):
        assert ADBInterface.is_device_connected() is False

def test_is_device_connected_serial_matches(mock_subprocess):
    """Test is_device_connected when DEVICE_SERIAL matches one of several connected devices."""
    mock_subprocess.return_value = MagicMock(stdout="List of devices attached\nAAA\tdevice\nBBB\tdevice\n")

    with patch.object(config, "DEVICE_SERIAL", "BBB"):
        assert ADBInterface.is_device_connected() is True

def test_is_device_connected_serial_not_found(mock_subprocess):
    """Test is_device_connected when DEVICE_SERIAL doesn't match any connected device."""
    mock_subprocess.return_value = MagicMock(stdout="List of devices attached\nAAA\tdevice\n")

    with patch.object(config, "DEVICE_SERIAL", "ZZZ"):
        assert ADBInterface.is_device_connected() is False

def test_is_app_installed_true(mock_subprocess):
    """Test is_app_installed when the package is present."""
    mock_subprocess.return_value = MagicMock(stdout="package:com.supercell.clashroyale\n")

    assert ADBInterface.is_app_installed("com.supercell.clashroyale") is True

def test_is_app_installed_false(mock_subprocess):
    """Test is_app_installed when the package is missing."""
    mock_subprocess.return_value = MagicMock(stdout="")

    assert ADBInterface.is_app_installed("com.supercell.clashroyale") is False

def test_is_app_installed_exact_match_only(mock_subprocess):
    """Test is_app_installed doesn't false-positive on a substring match from 'pm list packages'."""
    mock_subprocess.return_value = MagicMock(stdout="package:com.supercell.clashroyale.beta\n")

    assert ADBInterface.is_app_installed("com.supercell.clashroyale") is False

def test_is_device_locked_true(mock_subprocess):
    """Test is_device_locked when the trust dump reports deviceLocked=1."""
    mock_subprocess.return_value = MagicMock(stdout="deviceLocked=1, trustManaged=0")

    assert ADBInterface.is_device_locked() is True

def test_is_device_locked_false(mock_subprocess):
    """Test is_device_locked when the trust dump reports deviceLocked=0."""
    mock_subprocess.return_value = MagicMock(stdout="deviceLocked=0, trustManaged=0")

    assert ADBInterface.is_device_locked() is False

def test_is_device_locked_unknown_defaults_true(mock_subprocess):
    """Test is_device_locked falls back to locked (safe default) when the state can't be parsed."""
    mock_subprocess.return_value = MagicMock(stdout="")

    assert ADBInterface.is_device_locked() is True

def test_is_app_in_foreground_true(mock_subprocess):
    """Test is_app_in_foreground when the package owns the focused window."""
    mock_subprocess.return_value = MagicMock(
        stdout="  mFocusedApp=ActivityRecord{abc u0 com.supercell.clashroyale/com.supercell.titan.GameApp t1}\n"
    )

    assert ADBInterface.is_app_in_foreground("com.supercell.clashroyale") is True

def test_is_app_in_foreground_false(mock_subprocess):
    """Test is_app_in_foreground when a different app is focused."""
    mock_subprocess.return_value = MagicMock(
        stdout="  mFocusedApp=ActivityRecord{abc u0 com.android.launcher/.Launcher t1}\n"
    )

    assert ADBInterface.is_app_in_foreground("com.supercell.clashroyale") is False

def test_unlock_device_skips_swipe_and_pin_when_already_unlocked(mock_subprocess, mock_sleep):
    """Test unlock_device skips swipe/PIN entirely when the device is already unlocked."""
    responses = [
        MagicMock(stdout="mScreenState=ON"),  # dumpsys display
        MagicMock(stdout="deviceLocked=0"),   # dumpsys trust
    ]
    mock_subprocess.side_effect = responses

    with patch.object(config, "DEVICE_PIN", "1234"):
        ADBInterface.unlock_device()

    calls = [call[0][0] for call in mock_subprocess.call_args_list]
    assert not any("swipe" in cmd for cmd in calls)
    assert not any("text" in cmd for cmd in calls)

def test_launch_app_skips_when_already_in_foreground(mock_subprocess, mock_sleep):
    """Test launch_app skips the monkey command and wait when the app is already in foreground."""
    with patch.object(ADBInterface, 'unlock_device'), \
         patch.object(ADBInterface, 'is_app_in_foreground', return_value=True):
        ADBInterface.launch_app("com.test.app")

    calls = [call[0][0] for call in mock_subprocess.call_args_list]
    assert not any("monkey" in cmd for cmd in calls)
    mock_sleep.assert_not_called()

def test_base_cmd_default(mock_subprocess):
    """Test _base_cmd with no DEVICE_SERIAL configured."""
    with patch.object(config, "DEVICE_SERIAL", ""):
        assert ADBInterface._base_cmd() == ["adb"]

def test_base_cmd_with_serial(mock_subprocess):
    """Test _base_cmd targets the configured DEVICE_SERIAL."""
    with patch.object(config, "DEVICE_SERIAL", "AAA"):
        assert ADBInterface._base_cmd() == ["adb", "-s", "AAA"]

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

def test_unlock_device_no_pin(mock_subprocess, mock_sleep):
    """Test unlock_device does not type a PIN when DEVICE_PIN is unset."""
    mock_subprocess.return_value = MagicMock(stdout="mScreenState=ON", text=True)

    with patch.object(config, "DEVICE_PIN", ""):
        ADBInterface.unlock_device()

    calls = [call[0][0] for call in mock_subprocess.call_args_list]
    assert not any("text" in cmd for cmd in calls)
    assert not any("keyevent" in cmd and "66" in cmd for cmd in calls)

def test_unlock_device_with_pin(mock_subprocess, mock_sleep):
    """Test unlock_device types the configured PIN and confirms with Enter."""
    mock_subprocess.return_value = MagicMock(stdout="mScreenState=ON", text=True)

    with patch.object(config, "DEVICE_PIN", "1234"):
        ADBInterface.unlock_device()

    calls = [call[0][0] for call in mock_subprocess.call_args_list]
    assert any("text" in cmd and "1234" in cmd for cmd in calls)
    assert any("keyevent" in cmd and "66" in cmd for cmd in calls)

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
