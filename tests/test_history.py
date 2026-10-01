import pytest
from unittest.mock import patch
from config import config
from utils import history


@pytest.fixture(autouse=True)
def app_home(tmp_path):
    with patch.object(config, "APP_HOME", str(tmp_path / "home")):
        yield tmp_path / "home"


def test_recent_runs_empty_when_no_history():
    assert history.recent_runs(5) == []


def test_recent_runs_returns_last_n_oldest_first():
    for i in range(5):
        history.record_run({"command": "donate", "n": i})

    assert [r["n"] for r in history.recent_runs(3)] == [2, 3, 4]


def test_recent_runs_skips_corrupt_lines(app_home):
    history.record_run({"n": 1})
    with open(app_home / history.HISTORY_FILE_NAME, "a") as f:
        f.write('{"truncated\n')
    history.record_run({"n": 2})

    assert [r["n"] for r in history.recent_runs(10)] == [1, 2]


@pytest.mark.parametrize("entry,expected", [
    ({"free_card": "collected", "gold_deals": [500, 800]}, "free card collected, bought 2 (1300 gold)"),
    ({"free_card": "collected", "gold_deals": []}, "free card collected, nothing to buy"),
    ({"free_card": "failed", "gold_deals": "failed"}, "free card FAILED, gold deals FAILED"),
    ({"free_card": "skipped", "gold_deals": "skipped"}, "daily tasks already done today"),
    ({"donations": 12}, "12 donate tap(s)"),
    ({"error": "could not reach the Lobby"}, "could not reach the Lobby"),
    ({}, "-"),
])
def test_describe_run(entry, expected):
    assert history.describe_run(entry) == expected


def test_format_run():
    entry = {"start": "2026-10-02T10:00:03", "command": "daily", "ok": True, "free_card": "collected", "gold_deals": []}
    assert history.format_run(entry) == "2026-10-02 10:00  daily   OK    free card collected, nothing to buy"



def test_save_failure_screenshot_keeps_only_the_newest(app_home, tmp_path):
    import os
    from datetime import datetime, timedelta
    from utils import app_home as ah
    shot = tmp_path / "screen.png"
    shot.write_bytes(b"png")
    start = datetime(2026, 10, 1, 10, 0, 0)

    saved = [ah.save_failure_screenshot(str(shot), "lobby", now=start + timedelta(seconds=i))
             for i in range(ah.MAX_FAILURE_SCREENSHOTS + 3)]

    remaining = sorted(os.listdir(app_home / "debug" / "failures"))
    assert remaining == sorted(os.path.basename(p) for p in saved[-ah.MAX_FAILURE_SCREENSHOTS:])
    assert remaining[-1] == "20261001-100012-lobby.png"
    assert oct(os.stat(app_home).st_mode & 0o777) == "0o700"


def test_save_failure_screenshot_without_screenshot_returns_none(tmp_path):
    from utils.app_home import save_failure_screenshot
    assert save_failure_screenshot(str(tmp_path / "missing.png"), "lobby") is None
