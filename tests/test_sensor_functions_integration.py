# This software is provided 'as-is', without any express or
# implied warranty. In no event will ABB be held liable for
# any damages arising from the use of this software.

"""Tests for SensorFunctions.startSensor using the mock external sensor
(unreliable, can send incorrect data) and the mock PickMaster (reliable)."""

import threading
import time

import pytest

import SensorFunctions

from mocks.mock_external_sensor import MockExternalSensorServer
from mocks.mock_pickmaster import MockPickMaster


@pytest.fixture
def mock_sensor_server():
    server = MockExternalSensorServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture
def mock_pickmaster():
    return MockPickMaster()


def _start_sensor_thread(sensor, pickmaster, sensor_config_info, sensor_id="sensor-1", pos_gen_id="posgen-1"):
    thread = threading.Thread(
        target=sensor.startSensor,
        args=(pickmaster, sensor_id, pos_gen_id, sensor_config_info, "0", pickmaster, ""),
        daemon=True,
    )
    thread.start()
    return thread


def test_valid_acquisition_and_position_are_forwarded_to_pickmaster(mock_sensor_server, mock_pickmaster):
    sensor = SensorFunctions.SensorFunctions()
    sensor.isRunning = True
    sensorConfigInfo = "{};{}".format(mock_sensor_server.host, mock_sensor_server.port)

    thread = _start_sensor_thread(sensor, mock_pickmaster, sensorConfigInfo)
    try:
        assert mock_sensor_server.wait_for_client()

        mock_sensor_server.send_acquisition_trigger(1)
        mock_sensor_server.send_position_line(
            1,
            [
                {
                    "X": 100.0, "Y": 200.0, "RZ": 0.0, "Tag": 0, "Score": 1.0,
                    "Val1": 0.0, "Val2": 0.0, "Val3": 0.0, "Val4": 0.0, "Val5": 0.0, "Level": 2,
                }
            ],
        )

        assert mock_pickmaster.wait_for_position_count(1)
        position = mock_pickmaster.positions[0]
        assert position["SensorId"] == "sensor-1"
        assert position["'0'"]["X"] == 100.0
        assert position["'0'"]["Y"] == 200.0
        assert position["'0'"]["Tag"] == 0
        assert position["'0'"]["Level"] == 2
        assert position["'0'"]["PosGenId"] == "posgen-1"
        assert len(mock_pickmaster.strobe_times) == 1
    finally:
        sensor.isRunning = False
        if sensor.server is not None:
            sensor.server.close()
        thread.join(timeout=2)


def test_zero_objects_still_sends_position_with_no_objects(mock_sensor_server, mock_pickmaster):
    sensor = SensorFunctions.SensorFunctions()
    sensor.isRunning = True
    sensorConfigInfo = "{};{}".format(mock_sensor_server.host, mock_sensor_server.port)

    thread = _start_sensor_thread(sensor, mock_pickmaster, sensorConfigInfo)
    try:
        assert mock_sensor_server.wait_for_client()

        mock_sensor_server.send_acquisition_trigger(7)
        mock_sensor_server.send_position_line(7, [])

        assert mock_pickmaster.wait_for_position_count(1)
        position = mock_pickmaster.positions[0]
        assert position["SensorId"] == "sensor-1"
        assert "'0'" not in position
    finally:
        sensor.isRunning = False
        if sensor.server is not None:
            sensor.server.close()
        thread.join(timeout=2)


def test_incorrect_data_format_is_discarded_and_logged(mock_sensor_server, mock_pickmaster):
    # The external sensor can send garbage / incorrect data; ExternalSensorTCP
    # must not crash and must log the problem while continuing to operate.
    sensor = SensorFunctions.SensorFunctions()
    sensor.isRunning = True
    sensorConfigInfo = "{};{}".format(mock_sensor_server.host, mock_sensor_server.port)

    thread = _start_sensor_thread(sensor, mock_pickmaster, sensorConfigInfo)
    try:
        assert mock_sensor_server.wait_for_client()

        # Not a number / no comma structure that fails AcqNo parsing.
        mock_sensor_server.send_incorrect_data("not-a-valid-acqno")
        assert mock_pickmaster.wait_for_log_containing("Invalid text format")

        # Recovers afterwards and processes a valid acquisition/position pair.
        mock_sensor_server.send_acquisition_trigger(2)
        mock_sensor_server.send_position_line(
            2,
            [{"X": 1.0, "Y": 2.0, "RZ": 3.0, "Tag": 1, "Score": 0.9,
              "Val1": 0.0, "Val2": 0.0, "Val3": 0.0, "Val4": 0.0, "Val5": 0.0, "Level": 2}],
        )
        assert mock_pickmaster.wait_for_position_count(1)
    finally:
        sensor.isRunning = False
        if sensor.server is not None:
            sensor.server.close()
        thread.join(timeout=2)


def test_incorrect_field_count_position_line_is_rejected(mock_sensor_server, mock_pickmaster):
    sensor = SensorFunctions.SensorFunctions()
    sensor.isRunning = True
    sensorConfigInfo = "{};{}".format(mock_sensor_server.host, mock_sensor_server.port)

    thread = _start_sensor_thread(sensor, mock_pickmaster, sensorConfigInfo)
    try:
        assert mock_sensor_server.wait_for_client()

        mock_sensor_server.send_acquisition_trigger(3)
        # Declares 1 object but only sends a partial (incomplete) field block.
        mock_sensor_server.send_incorrect_data("3,1,100.0,200.0,0.0")

        assert mock_pickmaster.wait_for_log_containing("Invalid text format")
        # No position should have been forwarded for the malformed line.
        time.sleep(0.2)
        assert len(mock_pickmaster.positions) == 0
    finally:
        sensor.isRunning = False
        if sensor.server is not None:
            sensor.server.close()
        thread.join(timeout=2)


def test_position_before_trigger_is_discarded(mock_sensor_server, mock_pickmaster):
    sensor = SensorFunctions.SensorFunctions()
    sensor.isRunning = True
    sensorConfigInfo = "{};{}".format(mock_sensor_server.host, mock_sensor_server.port)

    thread = _start_sensor_thread(sensor, mock_pickmaster, sensorConfigInfo)
    try:
        assert mock_sensor_server.wait_for_client()

        # No prior acquisition trigger sent for AcqNo=99.
        mock_sensor_server.send_position_line(
            99,
            [{"X": 5.0, "Y": 6.0, "RZ": 0.0, "Tag": 0, "Score": 1.0,
              "Val1": 0.0, "Val2": 0.0, "Val3": 0.0, "Val4": 0.0, "Val5": 0.0, "Level": 1}],
        )

        # The position is silently discarded (no matching strobe time was
        # ever stored for AcqNo=99), so PickMaster never receives it.
        time.sleep(0.2)
        assert len(mock_pickmaster.positions) == 0
    finally:
        sensor.isRunning = False
        if sensor.server is not None:
            sensor.server.close()
        thread.join(timeout=2)


def test_client_disconnect_stops_worker_cleanly(mock_sensor_server, mock_pickmaster):
    sensor = SensorFunctions.SensorFunctions()
    sensor.isRunning = True
    sensorConfigInfo = "{};{}".format(mock_sensor_server.host, mock_sensor_server.port)

    thread = _start_sensor_thread(sensor, mock_pickmaster, sensorConfigInfo)
    try:
        assert mock_sensor_server.wait_for_client()
        mock_sensor_server.disconnect_client()
        thread.join(timeout=2)
        assert not thread.is_alive()
        assert mock_pickmaster.wait_for_log_containing("Socket closed/disconnected error!")
    finally:
        sensor.isRunning = False
        if sensor.server is not None:
            sensor.server.close()
