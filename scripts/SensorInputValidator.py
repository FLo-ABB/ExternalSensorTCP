import re


INVALID_POSITION_GENERATOR_INDEX_MESSAGE = "The entered index is invalid, please check your input."
DUPLICATE_POSITION_GENERATOR_INDEX_MESSAGE = "Duplicated index detected, please check your input."


def is_valid_ip_address(ip_address: str) -> bool:
    pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    if not re.match(pattern, ip_address):
        return False

    for part in ip_address.split("."):
        if int(part) < 0 or int(part) > 255:
            return False

    return True


def is_valid_port(port: str) -> bool:
    return bool(re.match(r"^\d+$", port)) and 0 <= int(port) <= 65535


def is_valid_sensor_endpoint(ip_address: str, port: str) -> bool:
    return is_valid_ip_address(ip_address) and is_valid_port(port)


def validate_position_generator_indexes(input_value: str) -> tuple[bool, str]:
    pattern = r"^(\d+;)+(?=\d+$)|^\d+$"
    if not re.match(pattern, input_value):
        return False, INVALID_POSITION_GENERATOR_INDEX_MESSAGE

    position_generator_index_list = re.findall(r"\d+", input_value)
    position_generator_index_set = set(position_generator_index_list)
    for index in position_generator_index_set:
        if position_generator_index_list.count(index) > 1:
            return False, DUPLICATE_POSITION_GENERATOR_INDEX_MESSAGE

    for index in position_generator_index_list:
        if int(index) < 0 or int(index) > 1000:
            return False, INVALID_POSITION_GENERATOR_INDEX_MESSAGE

    return True, ""
