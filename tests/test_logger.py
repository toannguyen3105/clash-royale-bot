import logging
from unittest.mock import patch
from utils.logger import setup_logger


def test_setup_logger_attaches_handlers_for_new_logger(tmp_path):
    log_file = tmp_path / "test.log"
    with patch.dict("os.environ", {"LOG_FILE": str(log_file)}):
        logger = setup_logger(name="test_logger_fresh")

    assert len(logger.handlers) == 2  # console + file


def test_setup_logger_is_idempotent(tmp_path):
    log_file = tmp_path / "test.log"
    with patch.dict("os.environ", {"LOG_FILE": str(log_file)}):
        logger1 = setup_logger(name="test_logger_idempotent")
        logger2 = setup_logger(name="test_logger_idempotent")

    assert logger1 is logger2
    assert len(logger1.handlers) == 2  # not duplicated on the second call


def test_setup_logger_ignores_root_logger_handlers(tmp_path):
    """Regression test: a handler already attached to the root logger (e.g. by
    pytest) must not prevent this logger's own handlers from being attached."""
    log_file = tmp_path / "test.log"
    root = logging.getLogger()
    dummy_handler = logging.NullHandler()
    root.addHandler(dummy_handler)
    try:
        with patch.dict("os.environ", {"LOG_FILE": str(log_file)}):
            logger = setup_logger(name="test_logger_root_handler")

        assert len(logger.handlers) == 2
    finally:
        root.removeHandler(dummy_handler)
