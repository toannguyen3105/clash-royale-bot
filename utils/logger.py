import logging
import logging.handlers
import sys
import os
from config import config
from utils.app_home import ensure_app_home, is_inside_app_home

# Rotate at ~1MB, keeping 5 old files, so an unattended scheduled bot can't
# grow the log without bound.
LOG_MAX_BYTES = 1_000_000
LOG_BACKUP_COUNT = 5

def setup_logger(name="bot", level=logging.INFO):
    """Set up logger based on the LOG_FILE environment variable (default: under APP_HOME)."""
    log_file = os.getenv("LOG_FILE", config.LOG_FILE)

    # Ensure the log directory exists (APP_HOME locked down first if it's inside it)
    log_dir = os.path.dirname(log_file)
    if log_dir:
        if is_inside_app_home(log_dir):
            ensure_app_home()
        os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers if the logger was already initialized.
    # Checking logger.handlers (not hasHandlers()) so an ancestor logger (e.g. root,
    # which pytest and other tools may attach a handler to) doesn't cause this to
    # skip setup for a "bot" logger that has no handlers of its own yet.
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Error: Could not initialize log file at {log_file}: {e}")

    return logger

# Singleton logger instance for the application
logger = setup_logger()
