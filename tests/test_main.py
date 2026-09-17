import pytest
from unittest.mock import patch
import main


@pytest.fixture
def mock_adb():
    with patch("main.ADBInterface") as mock:
        yield mock


@pytest.fixture
def mock_ensure_at_lobby():
    with patch("main.ensure_at_lobby") as mock:
        yield mock


@pytest.fixture
def mock_claim():
    with patch("main.claim_free_daily_card") as mock:
        yield mock


def test_main_fails_when_device_not_connected(mock_adb, mock_ensure_at_lobby, mock_claim):
    """Test main() returns False when no device is connected, without touching later steps."""
    mock_adb.is_device_connected.return_value = False

    assert main.main() is False
    mock_adb.is_app_installed.assert_not_called()
    mock_ensure_at_lobby.assert_not_called()
    mock_claim.assert_not_called()


def test_main_fails_when_app_not_installed(mock_adb, mock_ensure_at_lobby, mock_claim):
    """Test main() returns False when the game isn't installed."""
    mock_adb.is_device_connected.return_value = True
    mock_adb.is_app_installed.return_value = False

    assert main.main() is False
    mock_adb.launch_app.assert_not_called()
    mock_ensure_at_lobby.assert_not_called()
    mock_claim.assert_not_called()


def test_main_fails_when_lobby_not_confirmed(mock_adb, mock_ensure_at_lobby, mock_claim):
    """Test main() returns False when the Lobby can't be confirmed after launch."""
    mock_adb.is_device_connected.return_value = True
    mock_adb.is_app_installed.return_value = True
    mock_ensure_at_lobby.return_value = False

    assert main.main() is False
    mock_claim.assert_not_called()


def test_main_succeeds(mock_adb, mock_ensure_at_lobby, mock_claim):
    """Test main() returns True and claims the daily card once at the Lobby."""
    mock_adb.is_device_connected.return_value = True
    mock_adb.is_app_installed.return_value = True
    mock_ensure_at_lobby.return_value = True

    assert main.main() is True
    mock_claim.assert_called_once()
