"""Print the most recent bot runs:  python scripts/history.py [N]  (default 20)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.history import recent_runs, format_run  # noqa: E402

if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    runs = recent_runs(limit)
    if not runs:
        print("No runs recorded yet.")
    for entry in runs:
        print(format_run(entry))
