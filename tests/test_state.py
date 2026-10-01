import json
import os
from datetime import datetime
import pytest
from unittest.mock import patch
from config import config
from utils import state


@pytest.fixture(autouse=True)
def app_home(tmp_path):
    with patch.object(config, "APP_HOME", str(tmp_path / "home")):
        yield tmp_path / "home"


def test_game_day_follows_reset_hour():
    with patch("utils.state.DAILY_RESET_HOUR", 0):
        assert state.game_day(datetime(2026, 10, 1, 0, 5)) == "2026-10-01"
    with patch("utils.state.DAILY_RESET_HOUR", 7):
        assert state.game_day(datetime(2026, 10, 1, 6, 59)) == "2026-09-30"
        assert state.game_day(datetime(2026, 10, 1, 7, 0)) == "2026-10-01"


def test_task_is_done_only_on_the_day_it_was_marked():
    day1 = datetime(2026, 10, 1, 9, 0)
    day2 = datetime(2026, 10, 2, 9, 0)
    assert state.is_done_today("free_card", day1) is False

    state.mark_done_today("free_card", day1)

    assert state.is_done_today("free_card", day1) is True
    assert state.is_done_today("free_card", day2) is False
    assert state.is_done_today("gold_deals", day1) is False  # tracked per task


def test_mark_done_creates_private_app_home(app_home):
    state.mark_done_today("free_card")

    assert oct(os.stat(app_home).st_mode & 0o777) == "0o700"
    assert json.loads((app_home / "state.json").read_text())["free_card"] == state.game_day()


def test_corrupt_state_file_counts_as_nothing_done(app_home):
    app_home.mkdir()
    (app_home / "state.json").write_text("{not json")

    assert state.is_done_today("free_card") is False
    state.mark_done_today("free_card")  # and gets overwritten cleanly
    assert state.is_done_today("free_card") is True
