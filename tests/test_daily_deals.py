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


@pytest.fixture(autouse=True)
def mock_sleep():
    with patch("time.sleep"):
        yield


def _is_present_sequenced(**template_sequences):
    """Build an is_present(screen, template_path, threshold) side_effect where each
    template has its own sequence of return values, consumed in order as that
    specific template is checked; the last value repeats once a sequence is
    exhausted. Reads as a timeline of world-state per template, independent of
    the exact interleaving/count of internal calls."""
    state = {}

    def side_effect(screen_path, template_path, threshold):
        seq = template_sequences.get(template_path)
        if not seq:
            return False
        idx = state.get(template_path, 0)
        state[template_path] = idx + 1
        return seq[idx] if idx < len(seq) else seq[-1]

    return side_effect


# Where the popup's FREE! button / close-X templates match, and the centers that should be tapped.
POPUP_BUTTON_MATCH = (380, 1553)
POPUP_BUTTON_CENTER = (540, 1613)
POPUP_CLOSE_MATCH = (920, 870)
POPUP_CLOSE_CENTER = (965, 900)


def _find_all_by_template(**matches):
    """Build a find_all(screen, template_path, threshold) side_effect returning a
    fixed match list per template (empty for any template not listed)."""
    return lambda screen_path, template_path, threshold: matches.get(template_path, [])


def test_claim_free_daily_card_already_claimed(mock_adb, mock_detector):
    """Test claim_free_daily_card when the free slot was already collected today."""
    mock_detector.is_present.side_effect = _is_present_sequenced(**{
        daily_deals.DAILY_DEALS_BANNER_TEMPLATE: [True],
        daily_deals.DAILY_DEAL_COLLECTED_BADGE_TEMPLATE: [True],
    })

    result = daily_deals.claim_free_daily_card()

    assert result is True  # today's free card is collected, nothing left to do
    # Only the Shop nav tap should happen, never a tap on the free slot itself.
    tapped_points = [call.args for call in mock_adb.tap.call_args_list]
    assert daily_deals.FREE_SLOT_CENTER not in tapped_points
    assert POPUP_BUTTON_CENTER not in tapped_points


def test_claim_free_daily_card_success_with_confirm_popup(mock_adb, mock_detector):
    """Test claim_free_daily_card taps the confirmation popup's FREE! button too --
    the free slot opens a "Get X?" popup that must be confirmed to actually claim it."""
    mock_detector.is_present.side_effect = _is_present_sequenced(**{
        daily_deals.DAILY_DEALS_BANNER_TEMPLATE: [True],
        daily_deals.DAILY_DEAL_COLLECTED_BADGE_TEMPLATE: [False, True],
    })
    mock_detector.find_all.side_effect = _find_all_by_template(**{
        daily_deals.DAILY_DEAL_CONFIRM_POPUP_TEMPLATE: [POPUP_BUTTON_MATCH],
        daily_deals.DAILY_DEAL_POPUP_CLOSE_BUTTON_TEMPLATE: [POPUP_CLOSE_MATCH],
    })

    result = daily_deals.claim_free_daily_card()

    assert result is True
    tapped_points = [call.args for call in mock_adb.tap.call_args_list]
    assert daily_deals.FREE_SLOT_CENTER in tapped_points
    assert POPUP_BUTTON_CENTER in tapped_points
    # The popup stays open showing "Purchased!" and must be closed to reveal the badge.
    assert tapped_points[-1] == POPUP_CLOSE_CENTER


def test_claim_free_daily_card_success_without_confirm_popup(mock_adb, mock_detector):
    """Test claim_free_daily_card still succeeds with a single tap if no popup shows up."""
    mock_detector.is_present.side_effect = _is_present_sequenced(**{
        daily_deals.DAILY_DEALS_BANNER_TEMPLATE: [True],
        daily_deals.DAILY_DEAL_COLLECTED_BADGE_TEMPLATE: [False, True],
    })
    mock_detector.find_all.return_value = []

    result = daily_deals.claim_free_daily_card()

    assert result is True
    tapped_points = [call.args for call in mock_adb.tap.call_args_list]
    assert daily_deals.FREE_SLOT_CENTER in tapped_points
    assert POPUP_BUTTON_CENTER not in tapped_points


def test_claim_free_daily_card_tap_unconfirmed(mock_adb, mock_detector):
    """Test claim_free_daily_card when tapping (and confirming) doesn't result in a
    confirmed claim."""
    mock_detector.is_present.side_effect = _is_present_sequenced(**{
        daily_deals.DAILY_DEALS_BANNER_TEMPLATE: [True],
        daily_deals.DAILY_DEAL_COLLECTED_BADGE_TEMPLATE: [False, False],
    })
    mock_detector.find_all.side_effect = _find_all_by_template(**{
        daily_deals.DAILY_DEAL_CONFIRM_POPUP_TEMPLATE: [POPUP_BUTTON_MATCH],
        daily_deals.DAILY_DEAL_POPUP_CLOSE_BUTTON_TEMPLATE: [POPUP_CLOSE_MATCH],
    })

    result = daily_deals.claim_free_daily_card()

    assert result is False


def test_claim_free_daily_card_navigation_fails(mock_adb, mock_detector):
    """Test claim_free_daily_card when the Daily Deals screen is never reached."""
    mock_detector.is_present.return_value = False  # banner never found, any number of attempts

    result = daily_deals.claim_free_daily_card()

    assert result is False
    assert mock_adb.tap.call_count == daily_deals.MAX_SHOP_NAV_ATTEMPTS


def test_go_to_daily_deals_does_not_tap_when_already_there(mock_adb, mock_detector):
    """Test go_to_daily_deals doesn't tap Shop if Daily Deals is already showing --
    another tap would jump to the next Shop section, away from it."""
    mock_detector.is_present.return_value = True

    assert daily_deals.go_to_daily_deals() is True
    mock_adb.tap.assert_not_called()
