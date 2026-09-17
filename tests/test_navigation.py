import pytest
from unittest.mock import patch
from tasks import navigation


@pytest.fixture
def mock_adb():
    with patch("tasks.navigation.ADBInterface") as mock:
        yield mock


@pytest.fixture
def mock_detector():
    with patch("tasks.navigation.Detector") as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_sleep():
    with patch("time.sleep"):
        yield


def test_ensure_at_lobby_already_there(mock_adb, mock_detector):
    """Test ensure_at_lobby when the Lobby is detected on the first check."""
    mock_detector.is_present.return_value = True

    assert navigation.ensure_at_lobby() is True
    mock_adb.tap.assert_not_called()


def test_ensure_at_lobby_recovers_via_battle_nav(mock_adb, mock_detector):
    """Test ensure_at_lobby taps the Battle nav icon to back out of another screen."""
    mock_detector.is_present.side_effect = [False, True]

    assert navigation.ensure_at_lobby() is True
    mock_adb.tap.assert_called_once_with(*navigation.BATTLE_NAV_ICON)


def test_ensure_at_lobby_gives_up_after_max_attempts(mock_adb, mock_detector):
    """Test ensure_at_lobby returns False after exhausting all retry attempts."""
    mock_detector.is_present.return_value = False

    assert navigation.ensure_at_lobby() is False
    assert mock_adb.tap.call_count == navigation.MAX_LOBBY_RETURN_ATTEMPTS
