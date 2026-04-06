import logging
import sys
import os

def setup_logger(name="bot", level=logging.INFO):
    """Set up logger based on the LOG_FILE environment variable."""
    # Get log file path from .env, default to logs/bot.log
    log_file = os.getenv("LOG_FILE", "logs/bot.log")
    
    # Ensure the log directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger(name)
    
    # Prevet duplicate handlers if the logger was already initialized
    if logger.hasHandlers():
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    try:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Error: Could not initialize log file at {log_file}: {e}")

    return logger

# Singleton logger instance for the application
logger = setup_logger()
