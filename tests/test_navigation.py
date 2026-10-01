import pytest
from unittest.mock import patch
from tasks import navigation
from config import config


@pytest.fixture
def mock_adb():
    with patch("tasks.navigation.ADBInterface") as mock:
        yield mock


@pytest.fixture
def mock_detector():
    with patch("tasks.navigation.Detector") as mock:
        mock.find_all.return_value = []  # Battle nav icon not found unless a test says otherwise
        yield mock


@pytest.fixture(autouse=True)
def mock_sleep():
    with patch("time.sleep"):
        yield


def _is_present_by_template(lobby=(), chat_ok=()):
    """Build an is_present side_effect with a sequence of return values per template
    (the last value repeats once exhausted; False for any unlisted template)."""
    sequences = {config.TEMPLATE_PATH: list(lobby), navigation.CHAT_OK_BUTTON_TEMPLATE: list(chat_ok)}
    state = {}

    def side_effect(screen_path, template_path, threshold):
        seq = sequences.get(template_path)
        if not seq:
            return False
        idx = state.get(template_path, 0)
        state[template_path] = idx + 1
        return seq[idx] if idx < len(seq) else seq[-1]

    return side_effect


def test_ensure_at_lobby_already_there(mock_adb, mock_detector):
    """Test ensure_at_lobby when the Lobby is detected on the first check."""
    mock_detector.is_present.return_value = True

    assert navigation.ensure_at_lobby() is True
    mock_adb.tap.assert_not_called()


def test_ensure_at_lobby_taps_battle_icon_where_found(mock_adb, mock_detector):
    """Test ensure_at_lobby taps the center of the Battle nav icon wherever it's
    matched, since its position shifts with the selected tab (e.g. on Social)."""
    mock_detector.is_present.side_effect = _is_present_by_template(lobby=[False, True])
    mock_detector.find_all.return_value = [(385, 2245)]

    assert navigation.ensure_at_lobby() is True
    mock_adb.tap.assert_called_once_with(455, 2305)


def test_ensure_at_lobby_ignores_icon_matches_outside_nav_bar(mock_adb, mock_detector):
    """Test a Battle icon match above the nav bar isn't tapped (falls back instead)."""
    mock_detector.is_present.side_effect = _is_present_by_template(lobby=[False, True])
    mock_detector.find_all.return_value = [(400, 1200)]

    assert navigation.ensure_at_lobby() is True
    mock_adb.tap.assert_called_once_with(*navigation.BATTLE_NAV_ICON_FALLBACK)


def test_ensure_at_lobby_dismisses_chat_overlay_first(mock_adb, mock_detector):
    """Test the chat overlay's OK button is tapped before the Battle icon, since the
    overlay covers the nav bar."""
    mock_detector.is_present.side_effect = _is_present_by_template(lobby=[False, True], chat_ok=[True])
    mock_detector.find_all.return_value = [(385, 2245)]

    assert navigation.ensure_at_lobby() is True
    tapped_points = [call.args for call in mock_adb.tap.call_args_list]
    assert tapped_points == [navigation.CHAT_OK_BUTTON, (455, 2305)]


def test_ensure_at_lobby_succeeds_on_last_attempt(mock_adb, mock_detector):
    """Test the final attempt's tap still counts if it reaches the Lobby."""
    attempts = navigation.MAX_LOBBY_RETURN_ATTEMPTS
    mock_detector.is_present.side_effect = _is_present_by_template(lobby=[False] * attempts + [True])

    assert navigation.ensure_at_lobby() is True
    assert mock_adb.tap.call_count == attempts


def test_ensure_at_lobby_gives_up_after_max_attempts(mock_adb, mock_detector):
    """Test ensure_at_lobby returns False after exhausting all retry attempts."""
    mock_detector.is_present.return_value = False

    assert navigation.ensure_at_lobby() is False
    assert mock_adb.tap.call_count == navigation.MAX_LOBBY_RETURN_ATTEMPTS
