import pytest
from unittest.mock import patch, MagicMock
from tasks import daily_deals


@pytest.fixture
def mock_adb():
    with patch("tasks.daily_deals.ADBInterface") as mock:
        yield mock


@pytest.fixture
def mock_detector():
    with patch("tasks.daily_deals.Detector") as mock:
        yield mock


@pytest.fixture
def mock_discord():
    with patch("tasks.daily_deals.send_discord_message") as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_sleep():
    with patch("time.sleep"):
        yield


def test_claim_free_daily_card_already_claimed(mock_adb, mock_detector, mock_discord):
    """Test claim_free_daily_card when the free slot was already collected today."""
    mock_detector.is_present.side_effect = [True, True]  # banner found, then collected badge found

    result = daily_deals.claim_free_daily_card()

    assert result is False
    mock_discord.assert_called_once()
    # Only the Shop nav tap should happen, never a tap on the free slot itself.
    tapped_points = [call.args for call in mock_adb.tap.call_args_list]
    assert daily_deals.FREE_SLOT_CENTER not in tapped_points


def test_claim_free_daily_card_success(mock_adb, mock_detector, mock_discord):
    """Test claim_free_daily_card when the free slot is unclaimed and gets tapped successfully."""
    mock_detector.is_present.side_effect = [True, False, True]  # banner, not collected yet, now collected

    result = daily_deals.claim_free_daily_card()

    assert result is True
    mock_discord.assert_called_once()
    tapped_points = [call.args for call in mock_adb.tap.call_args_list]
    assert daily_deals.FREE_SLOT_CENTER in tapped_points


def test_claim_free_daily_card_tap_unconfirmed(mock_adb, mock_detector, mock_discord):
    """Test claim_free_daily_card when tapping the free slot doesn't result in a confirmed claim."""
    mock_detector.is_present.side_effect = [True, False, False]  # banner, not collected, still not collected

    result = daily_deals.claim_free_daily_card()

    assert result is False
    mock_discord.assert_not_called()


def test_claim_free_daily_card_navigation_fails(mock_adb, mock_detector, mock_discord):
    """Test claim_free_daily_card when the Daily Deals screen is never reached."""
    mock_detector.is_present.return_value = False  # banner never found, any number of attempts

    result = daily_deals.claim_free_daily_card()

    assert result is False
    mock_discord.assert_not_called()
    assert mock_adb.tap.call_count == daily_deals.MAX_SHOP_NAV_ATTEMPTS
