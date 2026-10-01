import pytest
from unittest.mock import patch
import main
from config import config


@pytest.fixture(autouse=True)
def mock_adb():
    with patch("main.ADBInterface") as mock:
        mock.is_device_connected.return_value = True
        mock.is_app_installed.return_value = True
        yield mock


@pytest.fixture(autouse=True)
def mock_ensure_at_lobby():
    with patch("main.ensure_at_lobby", return_value=True) as mock:
        yield mock


# All tasks are always mocked: otherwise main() would drive whatever device is connected.
@pytest.fixture(autouse=True)
def mock_claim():
    with patch("main.claim_free_daily_card", return_value=True) as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_buy_gold():
    with patch("main.buy_gold_daily_deals", return_value=[]) as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_donate():
    with patch("main.donate_all_requested_cards", return_value=0) as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_discord():
    with patch("main.send_discord_message") as mock:
        yield mock


@pytest.fixture(autouse=True)
def fresh_state(tmp_path):
    """Each test gets its own empty APP_HOME (state file + lock)."""
    with patch.object(config, "APP_HOME", str(tmp_path)):
        yield


@pytest.fixture(autouse=True)
def mock_sleep():
    with patch("main.time.sleep") as mock:
        yield mock


def test_main_fails_when_device_not_connected(mock_adb, mock_ensure_at_lobby, mock_claim, mock_discord):
    """Test main() returns False when no device is connected, without touching later steps."""
    mock_adb.is_device_connected.return_value = False

    assert main.main([]) is False
    mock_adb.is_app_installed.assert_not_called()
    mock_ensure_at_lobby.assert_not_called()
    mock_claim.assert_not_called()
    mock_discord.assert_called_once()  # failure is reported


def test_main_fails_when_app_not_installed(mock_adb, mock_ensure_at_lobby, mock_claim):
    """Test main() returns False when the game isn't installed."""
    mock_adb.is_app_installed.return_value = False

    assert main.main([]) is False
    mock_adb.launch_app.assert_not_called()
    mock_ensure_at_lobby.assert_not_called()
    mock_claim.assert_not_called()


def test_main_fails_when_lobby_not_confirmed(mock_ensure_at_lobby, mock_claim):
    """Test main() returns False when the Lobby can't be confirmed after launch."""
    mock_ensure_at_lobby.return_value = False

    assert main.main([]) is False
    mock_claim.assert_not_called()


def test_main_restarts_app_if_resumed_game_cant_reach_lobby(mock_adb, mock_ensure_at_lobby, mock_donate):
    """Test a run that skipped the restart (donate) falls back to one cold restart
    when the resumed game is stuck on a screen it can't back out of."""
    mock_ensure_at_lobby.side_effect = [False, True]

    assert main.main(["donate"]) is True
    mock_adb.force_stop_app.assert_called_once()
    mock_donate.assert_called_once()


def test_main_does_not_restart_twice_if_already_restarted(mock_adb, mock_ensure_at_lobby):
    mock_ensure_at_lobby.return_value = False

    with patch.object(config, "RESTART_APP_ON_START", True):
        assert main.main(["daily"]) is False

    mock_adb.force_stop_app.assert_called_once()


def test_main_all_runs_every_task(mock_claim, mock_buy_gold, mock_donate):
    """Test the default command runs the daily tasks and donations once."""
    assert main.main([]) is True
    mock_claim.assert_called_once()
    mock_buy_gold.assert_called_once()
    mock_donate.assert_called_once()


def test_main_daily_sends_one_success_summary(mock_buy_gold, mock_discord):
    mock_buy_gold.return_value = [500, 800]

    assert main.main(["daily"]) is True

    mock_discord.assert_called_once()
    message = mock_discord.call_args.args[0]
    assert message.startswith("✅")
    assert "free card collected" in message and "bought 2 (1300 gold)" in message


def test_main_daily_retry_with_everything_done_stays_silent(mock_discord):
    assert main.main(["daily"]) is True
    mock_discord.reset_mock()

    assert main.main(["daily"]) is True
    mock_discord.assert_not_called()


def test_main_records_one_history_line_per_run(mock_buy_gold, mock_donate):
    from utils.history import recent_runs
    mock_buy_gold.return_value = [500]
    mock_donate.return_value = 7

    main.main(["daily"])
    main.main(["donate"])

    daily, donate = recent_runs(10)
    assert daily["command"] == "daily" and daily["ok"] is True
    assert daily["free_card"] == "collected" and daily["gold_deals"] == [500]
    assert donate["command"] == "donate" and donate["donations"] == 7
    assert daily["start"] <= daily["end"]


def test_main_records_history_for_lobby_failure(mock_ensure_at_lobby):
    from utils.history import recent_runs
    mock_ensure_at_lobby.return_value = False

    main.main(["daily"])

    (entry,) = recent_runs(10)
    assert entry["ok"] is False and entry["error"] == "could not reach the Lobby"


def test_main_records_history_even_when_a_task_crashes(mock_donate):
    from utils.history import recent_runs
    mock_donate.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError):
        main.main(["donate"])

    (entry,) = recent_runs(10)
    assert entry["ok"] is False and entry["error"] == "crashed: RuntimeError: boom"


def test_main_records_history_when_skipped_for_lock():
    from utils.history import recent_runs
    from utils.run_lock import single_run_lock

    with single_run_lock():
        main.main(["donate"])

    (entry,) = recent_runs(10)
    assert entry["ok"] is False and entry["error"] == "skipped: another run in progress"


def test_main_daily_does_not_donate(mock_claim, mock_buy_gold, mock_donate):
    assert main.main(["daily"]) is True
    mock_claim.assert_called_once()
    mock_buy_gold.assert_called_once()
    mock_donate.assert_not_called()


def test_main_donate_does_not_touch_daily_deals(mock_claim, mock_buy_gold, mock_donate):
    assert main.main(["donate"]) is True
    mock_claim.assert_not_called()
    mock_buy_gold.assert_not_called()
    mock_donate.assert_called_once()


def test_main_daily_skips_tasks_already_done_today(mock_claim, mock_buy_gold):
    """Test a second daily run the same game day doesn't redo finished tasks."""
    assert main.main(["daily"]) is True
    assert main.main(["daily"]) is True

    mock_claim.assert_called_once()
    mock_buy_gold.assert_called_once()


def test_main_daily_retries_only_the_failed_task(mock_claim, mock_buy_gold, mock_discord):
    """Test a task that failed is retried on the next run, while one that succeeded isn't."""
    mock_claim.return_value = False

    assert main.main(["daily"]) is False
    mock_discord.assert_called_once()  # partial failure is reported

    mock_claim.return_value = True
    assert main.main(["daily"]) is True

    assert mock_claim.call_count == 2
    mock_buy_gold.assert_called_once()


def test_main_daily_does_not_mark_gold_deals_done_if_screen_unreachable(mock_buy_gold):
    mock_buy_gold.return_value = None  # couldn't reach Daily Deals

    assert main.main(["daily"]) is False
    mock_buy_gold.return_value = []
    assert main.main(["daily"]) is True
    assert mock_buy_gold.call_count == 2


@pytest.mark.parametrize("command,enabled,expect_restart", [
    ("all", True, True),
    ("daily", True, True),
    ("daily", False, False),
    ("donate", True, False),  # donate never pays for a cold start
])
def test_main_force_stops_app_before_launch(mock_adb, command, enabled, expect_restart):
    """Test RESTART_APP_ON_START controls whether the app is force-stopped (never for
    donate), and that the force-stop happens before launching."""
    with patch.object(config, "RESTART_APP_ON_START", enabled):
        assert main.main([command]) is True

    calls = [name for name, _, _ in mock_adb.method_calls if name in ("force_stop_app", "launch_app")]
    assert calls == (["force_stop_app", "launch_app"] if expect_restart else ["launch_app"])


@pytest.mark.parametrize("enabled", [True, False])
def test_main_turns_screen_off_after_run_only_when_enabled(mock_adb, enabled):
    with patch.object(config, "SCREEN_OFF_AFTER_RUN", enabled):
        main.main([])

    assert mock_adb.turn_screen_off.called is enabled


def test_main_turns_screen_off_even_when_a_task_crashes(mock_adb, mock_donate):
    mock_donate.side_effect = RuntimeError("boom")

    with patch.object(config, "SCREEN_OFF_AFTER_RUN", True), pytest.raises(RuntimeError):
        main.main(["donate"])

    mock_adb.turn_screen_off.assert_called_once()


def test_main_exits_without_doing_anything_if_another_run_holds_the_lock(mock_adb, mock_claim):
    from utils.run_lock import single_run_lock

    with single_run_lock() as acquired:
        assert acquired is True
        assert main.main([]) is False

    mock_adb.is_device_connected.assert_not_called()
    mock_claim.assert_not_called()


def test_main_jitter_waits_before_starting(mock_sleep):
    with patch("main.random.uniform", return_value=90.0) as mock_uniform:
        assert main.main(["donate", "--jitter-minutes", "5"]) is True

    mock_uniform.assert_called_once_with(0, 300)
    mock_sleep.assert_called_once_with(90.0)


def test_main_no_jitter_by_default(mock_sleep):
    assert main.main(["donate"]) is True
    mock_sleep.assert_not_called()


def test_main_saves_screenshot_when_lobby_not_reached(mock_ensure_at_lobby):
    mock_ensure_at_lobby.return_value = False
    with patch("main.save_failure_screenshot") as mock_save:
        main.main(["daily"])
    mock_save.assert_called_with(config.SCREENSHOT_PATH, "lobby")
