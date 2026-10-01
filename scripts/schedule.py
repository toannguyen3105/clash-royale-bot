"""Install/remove the bot's launchd jobs (macOS).

    python scripts/schedule.py install     # write plists to ~/Library/LaunchAgents and load them
    python scripts/schedule.py uninstall   # unload and delete them
    python scripts/schedule.py status      # show whether each job is loaded

Two jobs, both running `main.py` from this repo with its venv:
- daily:  10:00, retried at 15:00 -- during the day, when the Mac and phone are
          on (Daily Deals reset at ~00:00, so any time that day works). Tasks
          already done that game day are skipped, so the retry is a no-op when
          the first run succeeded.
- donate: every hour from 09:00 to 17:00 (working hours, when the Mac and phone
          are on), each run waiting a random 0-20 min first -- so the last
          one still finishes before 18:00.

launchd runs a missed StartCalendarInterval job once when the Mac wakes up, so
runs aren't silently lost to sleep (cron would just skip them). Overlapping runs
are prevented by main.py's run lock.

The plists only reference paths -- no secrets. PIN and webhook stay in .env.
"""
import os
import plistlib
import shutil
import subprocess
import sys

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)

from config import config  # noqa: E402
from constants import DEFAULT_DONATE_JITTER_MINUTES  # noqa: E402

LAUNCH_AGENTS_DIR = os.path.expanduser("~/Library/LaunchAgents")
LABEL_PREFIX = "com.clash-royale-bot"

JOBS = {
    "daily": {
        "args": ["daily"],
        "times": [{"Hour": 10, "Minute": 0}, {"Hour": 15, "Minute": 0}],
    },
    "donate": {
        "args": ["donate", "--jitter-minutes", str(DEFAULT_DONATE_JITTER_MINUTES)],
        "times": [{"Hour": hour, "Minute": 0} for hour in range(9, 18)],
    },
}


def _label(job):
    return f"{LABEL_PREFIX}.{job}"


def _plist_path(job):
    return os.path.join(LAUNCH_AGENTS_DIR, f"{_label(job)}.plist")


def _gui_domain():
    return f"gui/{os.getuid()}"


def build_plist(job):
    python = os.path.join(REPO_DIR, "venv", "bin", "python3")
    adb = shutil.which("adb")
    if not adb:
        sys.exit("adb not found on PATH; install it first (launchd needs its absolute location).")

    log_dir = os.path.join(config.APP_HOME, "logs")
    return {
        "Label": _label(job),
        "ProgramArguments": [python, os.path.join(REPO_DIR, "main.py"), *JOBS[job]["args"]],
        # .env and assets/templates/ are resolved relative to the repo.
        "WorkingDirectory": REPO_DIR,
        # launchd starts jobs with a minimal PATH (no Homebrew), so adb must be reachable explicitly.
        "EnvironmentVariables": {"PATH": f"{os.path.dirname(adb)}:/usr/bin:/bin:/usr/sbin:/sbin"},
        "StartCalendarInterval": JOBS[job]["times"],
        # Only stdout/stderr that escapes the bot's own logger (e.g. a crash traceback).
        "StandardOutPath": os.path.join(log_dir, f"launchd-{job}.log"),
        "StandardErrorPath": os.path.join(log_dir, f"launchd-{job}.log"),
    }


def install():
    from utils.app_home import ensure_app_home
    ensure_app_home()
    os.makedirs(os.path.join(config.APP_HOME, "logs"), exist_ok=True)
    os.makedirs(LAUNCH_AGENTS_DIR, exist_ok=True)

    for job in JOBS:
        path = _plist_path(job)
        # Re-installing: unload the old definition first so the new one takes effect.
        subprocess.run(["launchctl", "bootout", _gui_domain(), path], capture_output=True)
        with open(path, "wb") as f:
            plistlib.dump(build_plist(job), f)
        subprocess.run(["launchctl", "bootstrap", _gui_domain(), path], check=True)
        print(f"[V] Installed {_label(job)} -> {path}")


def uninstall():
    for job in JOBS:
        path = _plist_path(job)
        subprocess.run(["launchctl", "bootout", _gui_domain(), path], capture_output=True)
        if os.path.exists(path):
            os.remove(path)
        print(f"[V] Removed {_label(job)}")


def status():
    for job in JOBS:
        loaded = subprocess.run(["launchctl", "print", f"{_gui_domain()}/{_label(job)}"], capture_output=True).returncode == 0
        print(f"{_label(job)}: {'loaded' if loaded else 'not loaded'}")


if __name__ == "__main__":
    commands = {"install": install, "uninstall": uninstall, "status": status}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        sys.exit(f"usage: {sys.argv[0]} {{{'|'.join(commands)}}}")
    commands[sys.argv[1]]()
