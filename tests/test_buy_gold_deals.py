import pytest
from unittest.mock import patch
from tasks import buy_gold_deals as bgd
from config import config


class _TemplateWorld:
    """Minimal stateful fake for Detector.find_all/is_present keyed by template
    path, so tests read as "what's currently on screen" rather than depending
    on the exact call order/count inside the module under test."""

    def __init__(self):
        self.state = {}

    def set(self, template, value):
        self.state[template] = value

    def find_all(self, screen_path, template_path, threshold):
        return list(self.state.get(template_path, []))

    def is_present(self, screen_path, template_path, threshold):
        return bool(self.state.get(template_path, []))


@pytest.fixture
def mock_adb():
    with patch("tasks.buy_gold_deals.ADBInterface") as mock:
        yield mock


@pytest.fixture
def mock_detector():
    with patch("tasks.buy_gold_deals.Detector") as mock:
        yield mock


@pytest.fixture
def mock_discord():
    with patch("tasks.buy_gold_deals.send_discord_message") as mock:
        yield mock


@pytest.fixture
def mock_go_to_daily_deals():
    with patch("tasks.buy_gold_deals.go_to_daily_deals", return_value=True) as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_sleep():
    with patch("time.sleep"):
        yield


@pytest.fixture(autouse=True)
def max_gold_price():
    with patch.object(config, "MAX_GOLD_PRICE", 2000):
        yield


@pytest.fixture
def world(mock_detector):
    w = _TemplateWorld()
    mock_detector.find_all.side_effect = w.find_all
    mock_detector.is_present.side_effect = w.is_present
    return w


def test_buy_gold_deals_navigation_fails(mock_adb, mock_detector, mock_discord):
    """Test buy_gold_daily_deals when the Daily Deals screen is never reached."""
    with patch("tasks.buy_gold_deals.go_to_daily_deals", return_value=False):
        result = bgd.buy_gold_daily_deals()

    assert result == []
    mock_discord.assert_not_called()


def test_buy_gold_deals_no_slots_found(mock_adb, mock_go_to_daily_deals, mock_discord, world):
    """Test buy_gold_daily_deals when nothing gold-priced is visible."""
    result = bgd.buy_gold_daily_deals()

    assert result == []
    mock_discord.assert_not_called()


def test_buy_gold_deals_success(mock_adb, mock_go_to_daily_deals, mock_discord, world):
    """Test buy_gold_daily_deals buys a confirmed gold-priced slot end to end."""
    price_pos = (100, 100)
    grid_gold_icon = (price_pos[0] + bgd.PRICE_TO_ICON_OFFSET[0], price_pos[1] + bgd.PRICE_TO_ICON_OFFSET[1])
    popup_gold_icon = (500, 900)  # inside POPUP_REGION_Y_RANGE

    world.set(bgd.KNOWN_GOLD_PRICE_TEMPLATES[500], [price_pos])
    world.set(bgd.GOLD_ICON_TEMPLATE, [grid_gold_icon, popup_gold_icon])
    world.set(bgd.GEM_ICON_TEMPLATE, [])
    world.set(bgd.PURCHASED_BADGE_TEMPLATE, [price_pos])  # badge replaces the price text on success

    result = bgd.buy_gold_daily_deals()

    assert result == [500]
    mock_discord.assert_called_once()
    tapped_points = [call.args for call in mock_adb.tap.call_args_list]
    expected_slot_tap = (grid_gold_icon[0] + bgd.ICON_CENTER_OFFSET, grid_gold_icon[1] + bgd.ICON_CENTER_OFFSET)
    assert expected_slot_tap in tapped_points
    expected_popup_tap = (popup_gold_icon[0] + bgd.ICON_CENTER_OFFSET, popup_gold_icon[1] + bgd.ICON_CENTER_OFFSET)
    assert expected_popup_tap in tapped_points


def test_buy_gold_deals_success_despite_lingering_reward_popup(mock_adb, mock_go_to_daily_deals, mock_discord, world):
    """Regression test: a follow-up reward popup can show the same close-X style
    as the confirm popup after a successful purchase. That must not be read as
    "still failed" -- the 'Purchased!' badge on the slot is the real signal."""
    price_pos = (100, 100)
    grid_gold_icon = (price_pos[0] + bgd.PRICE_TO_ICON_OFFSET[0], price_pos[1] + bgd.PRICE_TO_ICON_OFFSET[1])
    popup_gold_icon = (500, 900)
    close_button_pos = (920, 870)

    world.set(bgd.KNOWN_GOLD_PRICE_TEMPLATES[500], [price_pos])
    world.set(bgd.GOLD_ICON_TEMPLATE, [grid_gold_icon, popup_gold_icon])
    world.set(bgd.GEM_ICON_TEMPLATE, [])
    world.set(bgd.PURCHASED_BADGE_TEMPLATE, [price_pos])
    world.set(bgd.POPUP_CLOSE_BUTTON_TEMPLATE, [close_button_pos])  # lingering reward popup

    result = bgd.buy_gold_daily_deals()

    assert result == [500]
    mock_discord.assert_called_once()


def test_buy_gold_deals_treats_missing_badge_as_failure(mock_adb, mock_go_to_daily_deals, mock_discord, world):
    """Test buy_gold_daily_deals reports failure (not a false success) if the
    'Purchased!' badge never shows up after confirming."""
    price_pos = (100, 100)
    grid_gold_icon = (price_pos[0] + bgd.PRICE_TO_ICON_OFFSET[0], price_pos[1] + bgd.PRICE_TO_ICON_OFFSET[1])
    popup_gold_icon = (500, 900)

    world.set(bgd.KNOWN_GOLD_PRICE_TEMPLATES[500], [price_pos])
    world.set(bgd.GOLD_ICON_TEMPLATE, [grid_gold_icon, popup_gold_icon])
    world.set(bgd.GEM_ICON_TEMPLATE, [])
    world.set(bgd.PURCHASED_BADGE_TEMPLATE, [])  # never appears

    result = bgd.buy_gold_daily_deals()

    assert result == []
    mock_discord.assert_not_called()


def test_buy_gold_deals_cancels_when_popup_shows_gem(mock_adb, mock_go_to_daily_deals, mock_discord, world):
    """Test buy_gold_daily_deals cancels (never confirms) if the popup that opens
    shows a gem icon instead of gold -- the critical never-buy-gem safety net."""
    price_pos = (100, 100)
    grid_gold_icon = (price_pos[0] + bgd.PRICE_TO_ICON_OFFSET[0], price_pos[1] + bgd.PRICE_TO_ICON_OFFSET[1])
    popup_gem_icon = (500, 900)  # inside POPUP_REGION_Y_RANGE
    close_button_pos = (920, 870)

    world.set(bgd.KNOWN_GOLD_PRICE_TEMPLATES[500], [price_pos])
    world.set(bgd.GOLD_ICON_TEMPLATE, [grid_gold_icon])  # only the grid icon, not in the popup
    world.set(bgd.GEM_ICON_TEMPLATE, [popup_gem_icon])
    world.set(bgd.POPUP_CLOSE_BUTTON_TEMPLATE, [close_button_pos])

    result = bgd.buy_gold_daily_deals()

    assert result == []
    mock_discord.assert_not_called()
    tapped_points = [call.args for call in mock_adb.tap.call_args_list]
    assert popup_gem_icon not in tapped_points  # never taps a gem-confirming button
    assert (close_button_pos[0] + 45, close_button_pos[1] + 30) in tapped_points


def test_buy_gold_deals_skips_price_above_cap(mock_adb, mock_go_to_daily_deals, mock_discord, world):
    """Test buy_gold_daily_deals never even attempts a slot priced above MAX_GOLD_PRICE."""
    price_pos = (100, 100)
    grid_gold_icon = (price_pos[0] + bgd.PRICE_TO_ICON_OFFSET[0], price_pos[1] + bgd.PRICE_TO_ICON_OFFSET[1])

    world.set(bgd.KNOWN_GOLD_PRICE_TEMPLATES[15000], [price_pos])
    world.set(bgd.GOLD_ICON_TEMPLATE, [grid_gold_icon])
    world.set(bgd.GEM_ICON_TEMPLATE, [])

    result = bgd.buy_gold_daily_deals()

    assert result == []
    mock_discord.assert_not_called()
    mock_adb.tap.assert_not_called()


def test_buy_gold_deals_skips_ambiguous_currency_icon(mock_adb, mock_go_to_daily_deals, mock_discord, world):
    """Test buy_gold_daily_deals skips a price match with no confirming gold icon
    nearby, rather than guessing it's safe to buy."""
    price_pos = (100, 100)

    world.set(bgd.KNOWN_GOLD_PRICE_TEMPLATES[500], [price_pos])
    world.set(bgd.GOLD_ICON_TEMPLATE, [])  # no gold icon anywhere near the price
    world.set(bgd.GEM_ICON_TEMPLATE, [])

    result = bgd.buy_gold_daily_deals()

    assert result == []
    mock_discord.assert_not_called()
    mock_adb.tap.assert_not_called()
