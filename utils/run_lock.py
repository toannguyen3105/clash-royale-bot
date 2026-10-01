import fcntl
import os
from contextlib import contextmanager
from config import config
from utils.app_home import ensure_app_home


@contextmanager
def single_run_lock():
    """Yield True if this process got the run lock, False if another bot run holds it.

    Every command drives the same phone, so two runs at once (e.g. a scheduled
    donate firing mid-way through a daily run) would interleave taps -- possibly
    onto a Shop purchase button. flock is released by the OS when the process
    exits, even on a crash or kill, so a stale lock can never block future runs.
    """
    ensure_app_home()
    lock_file = open(os.path.join(config.APP_HOME, "bot.lock"), "w")
    try:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
    finally:
        lock_file.close()
