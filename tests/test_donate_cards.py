import pytest
from unittest.mock import patch
from tasks import donate_cards


@pytest.fixture
def mock_adb():
    with patch("tasks.donate_cards.ADBInterface") as mock:
        yield mock


@pytest.fixture
def mock_detector():
    with patch("tasks.donate_cards.Detector") as mock:
        yield mock


@pytest.fixture
def mock_discord():
    with patch("tasks.donate_cards.send_discord_message") as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_sleep():
    with patch("time.sleep"):
        yield


def _find_all_by_template(banner_calls=(), disabled_calls=(), default_banner=(), default_disabled=()):
    """Build a find_all(screen, template_path, threshold) side_effect that tracks a
    separate call index per template, so tests read as a timeline of world-state
    per template rather than depending on the exact interleaving of internal calls."""
    state = {"banner": 0, "disabled": 0}

    def side_effect(screen_path, template_path, threshold):
        if template_path == donate_cards.REQUESTING_CARDS_TEMPLATE:
            idx = state["banner"]
            state["banner"] += 1
            return list(banner_calls[idx]) if idx < len(banner_calls) else list(default_banner)
        if template_path == donate_cards.DONATE_DISABLED_TEMPLATE:
            idx = state["disabled"]
            state["disabled"] += 1
            return list(disabled_calls[idx]) if idx < len(disabled_calls) else list(default_disabled)
        return []

    return side_effect


def test_donate_navigation_fails(mock_adb, mock_detector, mock_discord):
    """Test donate_all_requested_cards when the Chat feed is never reached."""
    mock_detector.is_present.return_value = False

    result = donate_cards.donate_all_requested_cards()

    assert result == 0
    mock_detector.find_all.assert_not_called()
    mock_discord.assert_not_called()
    assert mock_adb.tap.call_count == donate_cards.MAX_CHAT_NAV_ATTEMPTS


def test_donate_no_requests_gives_up_after_max_scrolls(mock_adb, mock_detector, mock_discord):
    """Test donate_all_requested_cards scrolls a bounded number of times when nothing is found."""
    mock_detector.is_present.return_value = True  # arrives at Chat immediately
    mock_detector.find_all.return_value = []  # never finds a request

    result = donate_cards.donate_all_requested_cards()

    assert result == 0
    assert mock_adb.swipe.call_count == donate_cards.MAX_SCROLL_ATTEMPTS
    # Regression guard: the feed anchors newest-at-bottom, so revealing older
    # requests means swiping down (finger starts high, ends low), not up.
    mock_adb.swipe.assert_called_with(*donate_cards.SCROLL_FROM, *donate_cards.SCROLL_TO)
    assert donate_cards.SCROLL_FROM[1] < donate_cards.SCROLL_TO[1]
    mock_discord.assert_not_called()


def test_donate_single_request_completes_after_several_taps(mock_adb, mock_detector, mock_discord):
    """Test donate_all_requested_cards keeps tapping one request until it disappears."""
    mock_detector.is_present.return_value = True
    mock_detector.find_all.side_effect = _find_all_by_template(
        banner_calls=[[(100, 100)], [(100, 100)], [(100, 100)], []],
        default_banner=[],
        default_disabled=[],  # never disabled
    )

    result = donate_cards.donate_all_requested_cards()

    assert result == 3  # 3 taps: 2 that found it still present, 1 that found it gone
    mock_discord.assert_called_once()


def test_donate_multiple_requests_processed_in_sequence(mock_adb, mock_detector, mock_discord):
    """Test donate_all_requested_cards moves on to the next request once one completes."""
    mock_detector.is_present.return_value = True
    mock_detector.find_all.side_effect = _find_all_by_template(
        # request A: present (topmost) -> tap -> gone (done, 1 tap)
        # request B: present (topmost) -> tap -> gone (done, 1 tap)
        banner_calls=[[(100, 100)], [], [(100, 200)], []],
        default_banner=[],
        default_disabled=[],
    )

    result = donate_cards.donate_all_requested_cards()

    assert result == 2
    mock_discord.assert_called_once()


def test_donate_skips_request_once_button_disabled(mock_adb, mock_detector, mock_discord):
    """Test donate_all_requested_cards moves on as soon as the Donate button grays out,
    without waiting for the banner itself to disappear or the safety cap."""
    mock_detector.is_present.return_value = True
    mock_detector.find_all.side_effect = _find_all_by_template(
        banner_calls=[[(100, 100)]],  # topmost check finds request A
        default_banner=[(100, 100)],  # banner never disappears (still pending, just capped)
        disabled_calls=[[], []],  # not disabled for the first 2 taps...
        default_disabled=[(100 + donate_cards.DONATE_DISABLED_OFFSET[0], 100 + donate_cards.DONATE_DISABLED_OFFSET[1])],  # ...then disabled
    )

    result = donate_cards.donate_all_requested_cards()

    assert result == 3  # 2 taps while active, 1 that revealed the disabled button
    mock_discord.assert_called_once()


def test_donate_skips_to_next_request_after_safety_cap(mock_adb, mock_detector, mock_discord):
    """Test donate_all_requested_cards gives up on a stuck request (safety cap) and still
    goes on to process a second request, rather than aborting the whole run."""
    mock_detector.is_present.return_value = True

    def side_effect(screen_path, template_path, threshold):
        if template_path == donate_cards.DONATE_DISABLED_TEMPLATE:
            return []  # never reports disabled
        if template_path == donate_cards.REQUESTING_CARDS_TEMPLATE:
            # Request A never disappears -> hits the safety cap and gets given up on.
            # Once given up, _topmost_request should skip it and find request B instead.
            return [(100, 100), (100, 300)]
        return []

    mock_detector.find_all.side_effect = side_effect

    result = donate_cards.donate_all_requested_cards()

    # MAX_TAPS_PER_REQUEST taps wasted on the stuck request A, then request B is found
    # and also never disappears in this mock, so it too runs to the safety cap.
    assert result == donate_cards.MAX_TAPS_PER_REQUEST * 2
    mock_discord.assert_called_once()


def _is_present_by_template(true_for=()):
    """Build an is_present(screen, template_path, threshold) side_effect that returns
    True only for the given template paths."""
    def side_effect(screen_path, template_path, threshold):
        return template_path in true_for
    return side_effect


def test_donate_dismisses_modal_when_present_after_run(mock_adb, mock_detector, mock_discord):
    """Test donate_all_requested_cards taps OK to close the New Messages modal
    once done, since it otherwise blocks the bottom nav bar for later tasks."""
    mock_detector.is_present.side_effect = _is_present_by_template(
        true_for=[donate_cards.CHAT_SCREEN_TEMPLATE, donate_cards.CHAT_OK_BUTTON_TEMPLATE]
    )
    mock_detector.find_all.return_value = []  # no requests, nothing to donate

    donate_cards.donate_all_requested_cards()

    tapped_points = [call.args for call in mock_adb.tap.call_args_list]
    assert donate_cards.CHAT_OK_BUTTON in tapped_points


def test_donate_does_not_tap_ok_when_modal_already_gone(mock_adb, mock_detector, mock_discord):
    """Test donate_all_requested_cards doesn't tap OK if the modal isn't showing."""
    mock_detector.is_present.side_effect = _is_present_by_template(
        true_for=[donate_cards.CHAT_SCREEN_TEMPLATE]  # arrives at Chat, but no OK modal
    )
    mock_detector.find_all.return_value = []

    donate_cards.donate_all_requested_cards()

    tapped_points = [call.args for call in mock_adb.tap.call_args_list]
    assert donate_cards.CHAT_OK_BUTTON not in tapped_points


def test_donate_hits_safety_cap_when_request_never_completes(mock_adb, mock_detector, mock_discord):
    """Test donate_all_requested_cards stops retrying after MAX_TAPS_PER_REQUEST if a
    request never disappears and its Donate button never reports disabled."""
    mock_detector.is_present.return_value = True
    mock_detector.find_all.side_effect = _find_all_by_template(
        default_banner=[(100, 100)],  # always present, never completes
        default_disabled=[],  # never disabled
    )

    result = donate_cards.donate_all_requested_cards()

    assert result == donate_cards.MAX_TAPS_PER_REQUEST
    mock_discord.assert_called_once()
