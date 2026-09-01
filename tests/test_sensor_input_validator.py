import pytest

import SensorInputValidator


# Verifies valid IPv4 addresses, including lower and upper octet boundaries.
# Expected result: all valid addresses are accepted.
@pytest.mark.parametrize("ip_address", ["0.0.0.0", "192.168.0.9", "255.255.255.255", "001.002.003.004"])
def test_valid_ip_addresses_are_accepted(ip_address):
    assert SensorInputValidator.is_valid_ip_address(ip_address) is True


# Verifies malformed and out-of-range IPv4 addresses are rejected.
# Expected result: invalid address strings are not accepted.
@pytest.mark.parametrize(
    "ip_address",
    ["", "192.168.0", "192.168.0.1.2", "192.168.0.a", "256.168.0.1", "192.168.0.-1"],
)
def test_invalid_ip_addresses_are_rejected(ip_address):
    assert SensorInputValidator.is_valid_ip_address(ip_address) is False


# Verifies TCP ports at numeric boundaries and inside the valid range.
# Expected result: numeric strings from 0 through 65535 are accepted.
@pytest.mark.parametrize("port", ["0", "1", "8500", "65535"])
def test_valid_ports_are_accepted(port):
    assert SensorInputValidator.is_valid_port(port) is True


# Verifies non-numeric and out-of-range TCP port values are rejected.
# Expected result: invalid port strings are not accepted.
@pytest.mark.parametrize("port", ["", "abc", "-1", "65536", "80.0", " 80"])
def test_invalid_ports_are_rejected(port):
    assert SensorInputValidator.is_valid_port(port) is False


# Verifies sensor endpoint validation combines IP and port checks.
# Expected result: both values must be valid before the endpoint is accepted.
def test_sensor_endpoint_requires_valid_ip_and_port():
    assert SensorInputValidator.is_valid_sensor_endpoint("192.168.0.9", "8500") is True
    assert SensorInputValidator.is_valid_sensor_endpoint("256.168.0.9", "8500") is False
    assert SensorInputValidator.is_valid_sensor_endpoint("192.168.0.9", "65536") is False


# Verifies one or more semicolon-separated position generator indexes are accepted.
# Expected result: unique indexes from 0 through 1000 are valid.
@pytest.mark.parametrize("input_value", ["0", "1", "1000", "0;1;1000"])
def test_valid_position_generator_indexes_are_accepted(input_value):
    is_valid, message = SensorInputValidator.validate_position_generator_indexes(input_value)

    assert is_valid is True
    assert message == ""


# Verifies malformed position generator index strings are rejected with the invalid message.
# Expected result: invalid syntax or out-of-range values return the invalid-index message.
@pytest.mark.parametrize("input_value", ["", "1;", ";1", "1;;2", "1,2", "-1", "1001", " 1"])
def test_invalid_position_generator_indexes_are_rejected(input_value):
    is_valid, message = SensorInputValidator.validate_position_generator_indexes(input_value)

    assert is_valid is False
    assert message == SensorInputValidator.INVALID_POSITION_GENERATOR_INDEX_MESSAGE


# Verifies duplicated position generator indexes are rejected with the duplicate message.
# Expected result: repeated values return the duplicate-index message.
@pytest.mark.parametrize("input_value", ["1;1", "1;2;1"])
def test_duplicate_position_generator_indexes_are_rejected(input_value):
    is_valid, message = SensorInputValidator.validate_position_generator_indexes(input_value)

    assert is_valid is False
    assert message == SensorInputValidator.DUPLICATE_POSITION_GENERATOR_INDEX_MESSAGE
