import json
import os
from config import config
from utils.app_home import ensure_app_home

# One JSON object per line, one line per bot run. Append-only and tiny (~200
# bytes/run), so unlike the rotating bot.log it keeps the full run history.
HISTORY_FILE_NAME = "runs.jsonl"


def _history_path():
    return os.path.join(config.APP_HOME, HISTORY_FILE_NAME)


def record_run(entry):
    ensure_app_home()
    with open(_history_path(), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def recent_runs(limit):
    """The last `limit` recorded runs, oldest first. Unparseable lines (e.g. a run
    killed mid-write) are skipped rather than breaking the whole history."""
    try:
        with open(_history_path(), encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return []

    runs = []
    for line in lines:
        try:
            runs.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return runs[-limit:]


def describe_run(entry):
    """One human-readable line summarizing a run's outcome."""
    parts = []

    free_card = entry.get("free_card")
    if free_card == "collected":
        parts.append("free card collected")
    elif free_card == "failed":
        parts.append("free card FAILED")

    gold_deals = entry.get("gold_deals")
    if isinstance(gold_deals, list):
        if gold_deals:
            parts.append(f"bought {len(gold_deals)} ({sum(gold_deals)} gold)")
        else:
            parts.append("nothing to buy")
    elif gold_deals == "failed":
        parts.append("gold deals FAILED")

    if free_card == "skipped" and gold_deals == "skipped":
        parts.append("daily tasks already done today")

    if entry.get("donations") is not None:
        parts.append(f"{entry['donations']} donate tap(s)")

    if entry.get("error"):
        parts.append(entry["error"])

    return ", ".join(parts) or "-"


def format_run(entry):
    start = entry.get("start", "?").replace("T", " ")[:16]
    status = "OK  " if entry.get("ok") else "FAIL"
    return f"{start}  {entry.get('command', '?'):<6}  {status}  {describe_run(entry)}"
