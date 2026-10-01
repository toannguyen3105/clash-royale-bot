"""Isolate the test suite from the developer's real environment.

This runs before any test module imports `config`, so these values win over
.env (python-dotenv never overrides variables already set in the environment):
- DISCORD_WEBHOOK_URL is blanked, so no code path can post to the real webhook.
- APP_HOME points at a throwaway directory, so state/lock/log files written by
  tests never touch ~/.clash-royale-bot (a fake "done today" state there would
  make the real bot skip that day's tasks).
"""
import atexit
import os
import shutil
import tempfile

_test_app_home = tempfile.mkdtemp(prefix="clash-royale-bot-tests-")
atexit.register(shutil.rmtree, _test_app_home, ignore_errors=True)

os.environ["APP_HOME"] = _test_app_home
os.environ["LOG_FILE"] = os.path.join(_test_app_home, "logs", "bot.log")
os.environ["SCREENSHOT_PATH"] = os.path.join(_test_app_home, "debug", "screen.png")
os.environ["DISCORD_WEBHOOK_URL"] = ""
