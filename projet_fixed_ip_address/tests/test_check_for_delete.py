import pytest

# importing sys
import sys
# adding Folder_2/subfolder to the system path
sys.path.insert(1, '/Users/user/github/kostya-1/projet_fixed_ip_address')
from nb_ipam_api import *

def device_exists_in_config(device_identifier: str, parent_path: str) -> bool:
    """
    Given a device identifier (MAC address, IP address, or name) and a parent path, this function checks if the device
    exists in the configuration file at the given path.

    Args:
        device_identifier (str): The device identifier to check (MAC address, IP address, or name).
        parent_path (str): The parent path of the configuration file.

    Returns:
        bool: True if the device exists in the configuration file, False otherwise.
    """
    # Open the configuration file and parse its contents
    with open(parent_path + "result.conf", "r") as f:
        conf = f.read()
        config = parser.parse(conf)
        dic_config = list(config[0]['host'])

    # Loop through each device name in the configuration file
    for dev_name in dic_config:
        # Get the `hardware` dictionary for the current device
        hardware = config[0]['host'][dev_name].get('hardware', {})

        # Check if the device identifier matches the MAC address, IP address, or name of the current device
        if device_identifier in hardware.values() or device_identifier in config[0]['host'][dev_name].values() or device_identifier == dev_name:
            return True

    # If the device identifier was not found, return False
    return False

def test_check_for_delete():
    # Test case 1: MAC address is found in configuration file
    mac_address = "00:11:22:33:44:55"
    device_name = ""
    ip_address = ""
    parent_path = "/path/to/file/"
    check_for_delete(mac_address, device_name, ip_address, parent_path)
    # Assert that the device with the MAC address was deleted
    assert not device_exists_in_config(mac_address, parent_path)

    # Test case 2: IP address is found in configuration file
    mac_address = ""
    device_name = ""
    ip_address = "192.168.1.100"
    parent_path = "/path/to/file/"
    check_for_delete(mac_address, device_name, ip_address, parent_path)
    # Assert that the device with the IP address was deleted
    assert not device_exists_in_config(ip_address, parent_path)

    # Test case 3: MAC address is not found in configuration file
    mac_address = "00:11:22:33:44:66"
    device_name = "device_3"
    ip_address = ""
    parent_path = "/path/to/file/"
    check_for_delete(mac_address, device_name, ip_address, parent_path)
    # Assert that the device with the passed device name was deleted
    assert not device_exists_in_config(device_name, parent_path)