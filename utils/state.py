import json
import os
from datetime import datetime, timedelta
from config import config
from constants import DAILY_RESET_HOUR
from utils.app_home import ensure_app_home


def _state_path():
    return os.path.join(config.APP_HOME, "state.json")


def game_day(now=None):
    """The in-game "day" (as an ISO date) that `now` falls in. Daily Deals reset
    at DAILY_RESET_HOUR local time, so e.g. 00:10 already counts as the new day."""
    now = now or datetime.now()
    return (now - timedelta(hours=DAILY_RESET_HOUR)).date().isoformat()


def _load():
    try:
        with open(_state_path(), encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # A missing or corrupt state file just means nothing is recorded as done,
        # so the next run re-checks everything on screen.
        return {}


def is_done_today(task, now=None):
    return _load().get(task) == game_day(now)


def mark_done_today(task, now=None):
    ensure_app_home()
    state = _load()
    state[task] = game_day(now)
    # Write to a temp file then rename, so a crash mid-write can't leave a
    # truncated state.json behind.
    tmp_path = _state_path() + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp_path, _state_path())
