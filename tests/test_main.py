import pytest
from unittest.mock import patch
import main
from config import config


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


# Not requested by every test, but must always be mocked: otherwise main() runs
# the real donate/buy tasks against whatever device is connected.
@pytest.fixture(autouse=True)
def mock_donate():
    with patch("main.donate_all_requested_cards") as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_buy_gold():
    with patch("main.buy_gold_daily_deals") as mock:
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


def test_main_succeeds(mock_adb, mock_ensure_at_lobby, mock_claim, mock_buy_gold, mock_donate):
    """Test main() returns True and runs the daily card claim, gold deal buying and donations once at the Lobby."""
    mock_adb.is_device_connected.return_value = True
    mock_adb.is_app_installed.return_value = True
    mock_ensure_at_lobby.return_value = True

    assert main.main() is True
    mock_claim.assert_called_once()
    mock_buy_gold.assert_called_once()
    mock_donate.assert_called_once()


@pytest.mark.parametrize("enabled", [True, False])
def test_main_force_stops_app_before_launch_only_when_enabled(mock_adb, mock_ensure_at_lobby, mock_claim, enabled):
    """Test RESTART_APP_ON_START controls whether the app is force-stopped, and that
    the force-stop happens before launching."""
    mock_adb.is_device_connected.return_value = True
    mock_adb.is_app_installed.return_value = True
    mock_ensure_at_lobby.return_value = True

    with patch.object(config, "RESTART_APP_ON_START", enabled):
        assert main.main() is True

    calls = [name for name, _, _ in mock_adb.method_calls if name in ("force_stop_app", "launch_app")]
    assert calls == (["force_stop_app", "launch_app"] if enabled else ["launch_app"])
