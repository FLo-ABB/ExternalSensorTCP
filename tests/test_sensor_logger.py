"""Tests for SensorLogger, covering the 50 MB size limit and the
circular rotation that keeps only the most recent rotated files."""

# Coverage:
# - Config serialization round-trips correctly.
# - Writing while disabled produces no file and no queued work.
# - Writing while enabled creates the log file with the expected line.
# - A log file at/over the size limit is rotated (renamed with a
#   timestamp suffix) before the next write, and a new file is started.
# - Rotation is circular: once more than MAX_ROTATED_LOG_FILES rotated
#   files exist, the oldest ones are pruned, keeping only the newest ones.
# - _rotate_log_file() is a no-op when the target file does not exist.

import glob
import os
import queue
import time

import pytest

from SensorLogger import SensorLogger, deserialize_config, serialize_config


@pytest.fixture(autouse=True)
def reset_logger_class_state():
    """SensorLogger keeps its queue/worker flags on the class, so
    reset them before every test to avoid cross-test contamination."""
    SensorLogger._write_queue = queue.Queue()
    SensorLogger._worker_started = False
    yield
    SensorLogger._write_queue = queue.Queue()
    SensorLogger._worker_started = False


def _make_logger(tmp_path, filename="ExternalSensor.log", enabled=True):
    config_str = serialize_config(enabled, str(tmp_path), filename)
    return SensorLogger(config_str)


def _wait_for_queue_drain(timeout=5.0):
    """Block until the background worker has processed all queued writes."""
    deadline = time.time() + timeout
    while not SensorLogger._write_queue.empty() and time.time() < deadline:
        time.sleep(0.01)
    # Give the worker a brief moment to finish its current item.
    SensorLogger._write_queue.join()


# Verifies that serializing a config and deserializing it back returns the
# same enabled flag, folder, and filename that were passed in.
def test_config_round_trip(tmp_path):
    config_str = serialize_config(True, str(tmp_path), "ExternalSensor.log")
    enabled, folder, filename = deserialize_config(config_str)
    assert enabled is True
    assert folder == str(tmp_path)
    assert filename == "ExternalSensor.log"


# Verifies that log() is a no-op when logging is disabled: nothing is
# queued and no log file is created.
def test_log_does_nothing_when_disabled(tmp_path):
    logger = _make_logger(tmp_path, enabled=False)

    logger.log("context", "message", success=True)
    _wait_for_queue_drain()

    assert SensorLogger._write_queue.empty()
    assert not os.path.exists(logger.log_path)


# Verifies that log() writes a single line with the timestamp, [SUCCESS]
# mark, context, and message when logging is enabled.
def test_log_writes_expected_line_when_enabled(tmp_path):
    logger = _make_logger(tmp_path)

    logger.log("MyContext", "hello world", success=True)
    _wait_for_queue_drain()

    assert os.path.exists(logger.log_path)
    with open(logger.log_path, "r", encoding="utf-8") as log_file:
        content = log_file.read()

    assert "[SUCCESS]" in content
    assert "[MyContext] hello world" in content
    assert content.endswith("\n")


# Verifies that log() marks the line as [ERROR] when success is False.
def test_log_writes_error_mark_when_not_success(tmp_path):
    logger = _make_logger(tmp_path)

    logger.log("MyContext", "boom", success=False)
    _wait_for_queue_drain()

    with open(logger.log_path, "r", encoding="utf-8") as log_file:
        content = log_file.read()

    assert "[ERROR]" in content
    assert "[MyContext] boom" in content


# Verifies that successive log() calls append new lines to the same file
# instead of overwriting previous entries.
def test_log_appends_multiple_lines(tmp_path):
    logger = _make_logger(tmp_path)

    logger.log("ctx1", "first", success=True)
    logger.log("ctx2", "second", success=False)
    _wait_for_queue_drain()

    with open(logger.log_path, "r", encoding="utf-8") as log_file:
        lines = log_file.readlines()

    assert len(lines) == 2
    assert "first" in lines[0]
    assert "second" in lines[1]


# Verifies that _rotate_log_file() does nothing when there is no current
# log file to rotate (no rename, no rotated file created).
def test_rotate_log_file_is_noop_when_file_missing(tmp_path):
    log_path = os.path.join(str(tmp_path), "ExternalSensor.log")

    SensorLogger._rotate_log_file(log_path)

    assert not os.path.exists(log_path)
    assert glob.glob(os.path.join(str(tmp_path), "ExternalSensor_*.log")) == []


# Verifies that _rotate_log_file() renames the current log file to a
# timestamped filename and preserves its content.
def test_rotate_log_file_renames_current_log_with_timestamp(tmp_path):
    log_path = os.path.join(str(tmp_path), "ExternalSensor.log")
    with open(log_path, "w", encoding="utf-8") as log_file:
        log_file.write("existing content\n")

    SensorLogger._rotate_log_file(log_path)

    assert not os.path.exists(log_path)
    rotated_files = glob.glob(os.path.join(str(tmp_path), "ExternalSensor_*.log"))
    assert len(rotated_files) == 1
    with open(rotated_files[0], "r", encoding="utf-8") as rotated_file:
        assert rotated_file.read() == "existing content\n"


# Verifies the circular rotation behavior: once more rotated files exist
# than MAX_ROTATED_LOG_FILES allows, the oldest ones are pruned so only
# the newest ones remain.
def test_rotate_log_file_keeps_only_the_5_newest_rotated_files(tmp_path):
    log_path = os.path.join(str(tmp_path), "ExternalSensor.log")
    base_name, extension = os.path.splitext(log_path)

    # Pre-create more rotated files than the cap allows, with distinct
    # mtimes so the oldest ones are unambiguous.
    extra_rotated_files = []
    for i in range(7):
        rotated_path = "{}_existing{}{}".format(base_name, i, extension)
        with open(rotated_path, "w", encoding="utf-8") as rotated_file:
            rotated_file.write("rotated {}\n".format(i))
        mtime = time.time() - (100 - i)
        os.utime(rotated_path, (mtime, mtime))
        extra_rotated_files.append(rotated_path)

    # Trigger one more rotation of the "current" log file.
    with open(log_path, "w", encoding="utf-8") as log_file:
        log_file.write("current\n")
    SensorLogger._rotate_log_file(log_path)

    rotated_files = glob.glob("{}_*{}".format(base_name, extension))
    assert len(rotated_files) == SensorLogger.MAX_ROTATED_LOG_FILES

    # 7 pre-existing + 1 newly rotated = 8 files; only the 5 newest survive,
    # i.e. the 3 oldest pre-existing files must have been pruned.
    for removed_file in extra_rotated_files[:3]:
        assert removed_file not in rotated_files
    for surviving_file in extra_rotated_files[3:]:
        assert surviving_file in rotated_files


# Verifies the end-to-end size-limit rotation: writing through log()
# rotates the file once it is at or above the configured size limit,
# without needing an actual 50 MB file (the limit is monkeypatched down
# for a fast, deterministic test).
def test_write_worker_rotates_log_when_size_limit_reached(tmp_path, monkeypatch):
    monkeypatch.setattr(SensorLogger, "MAX_LOG_FILE_SIZE_BYTES", 10)

    logger = _make_logger(tmp_path)
    log_path = logger.log_path
    base_name, extension = os.path.splitext(log_path)

    # First write: file doesn't exist yet, so no rotation should happen.
    logger.log("ctx", "a" * 20, success=True)
    _wait_for_queue_drain()
    assert os.path.exists(log_path)
    assert glob.glob("{}_*{}".format(base_name, extension)) == []
    assert os.path.getsize(log_path) >= SensorLogger.MAX_LOG_FILE_SIZE_BYTES

    # Second write: existing file is already >= the (patched) limit, so it
    # must be rotated before the new line is written to a fresh file.
    logger.log("ctx", "b", success=True)
    _wait_for_queue_drain()

    rotated_files = glob.glob("{}_*{}".format(base_name, extension))
    assert len(rotated_files) == 1
    assert os.path.exists(log_path)
    with open(log_path, "r", encoding="utf-8") as log_file:
        content = log_file.read()
    assert "a" not in content
    assert "b" in content
