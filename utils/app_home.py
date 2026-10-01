import os
import shutil
from datetime import datetime
from config import config


def ensure_app_home():
    """Create config.APP_HOME if needed and restrict it to the current user (700).

    Everything the bot writes at runtime (state, lock, logs, screenshots) lives
    under this one directory, outside the repo. Locking down just this directory
    is enough to keep its contents private: other users can't reach any file
    inside it, whatever that file's own mode is.
    """
    os.makedirs(config.APP_HOME, mode=0o700, exist_ok=True)
    os.chmod(config.APP_HOME, 0o700)


def is_inside_app_home(path):
    home = os.path.realpath(config.APP_HOME)
    return os.path.commonpath([home, os.path.realpath(path)]) == home


# Failure screenshots kept for diagnosis; older ones are pruned past this count.
MAX_FAILURE_SCREENSHOTS = 10


def save_failure_screenshot(screenshot_path, reason, now=None):
    """Keep a copy of `screenshot_path` as debug/failures/<timestamp>-<reason>.png,
    so a failure's screen survives the next capture overwriting screen.png.
    Returns the saved path, or None if there was no screenshot to keep."""
    if not os.path.exists(screenshot_path):
        return None

    ensure_app_home()
    failures_dir = os.path.join(config.APP_HOME, "debug", "failures")
    os.makedirs(failures_dir, exist_ok=True)
    saved = os.path.join(failures_dir, f"{now or datetime.now():%Y%m%d-%H%M%S}-{reason}.png")
    shutil.copyfile(screenshot_path, saved)

    for old in sorted(os.listdir(failures_dir))[:-MAX_FAILURE_SCREENSHOTS]:
        os.remove(os.path.join(failures_dir, old))
    return saved
