import pytest
from unittest.mock import patch
from config import config
from utils.run_lock import single_run_lock


@pytest.fixture(autouse=True)
def app_home(tmp_path):
    with patch.object(config, "APP_HOME", str(tmp_path)):
        yield


def test_second_holder_is_refused_while_first_holds_lock():
    with single_run_lock() as first:
        assert first is True
        with single_run_lock() as second:
            assert second is False


def test_lock_is_released_after_use():
    with single_run_lock() as first:
        assert first is True
    with single_run_lock() as again:
        assert again is True


def test_lock_is_released_when_the_holder_raises():
    with pytest.raises(RuntimeError):
        with single_run_lock():
            raise RuntimeError("boom")
    with single_run_lock() as again:
        assert again is True
