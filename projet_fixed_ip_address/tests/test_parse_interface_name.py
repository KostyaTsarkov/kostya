import pytest
# importing sys
import sys
# adding Folder_2/subfolder to the system path
sys.path.insert(1, 'C:\git_folder\kostya-1\projet_fixed_ip_address')
from common import parse_interface_name


# Tests that the function correctly extracts the interface type and ID from a valid Ethernet interface name. 
def test_happy_path_ethernet():
    result = parse_interface_name("Ethernet0")
    assert result == ("Ethernet", "0")

# Tests that the function correctly extracts the interface type and ID from a valid Serial interface name. 
def test_happy_path_serial():
    result = parse_interface_name("Serial1/0")
    assert result == ("Serial", "1/0")

# Tests that the function raises a ValueError when given an empty string. 
def test_empty_string():
    with pytest.raises(ValueError):
        parse_interface_name("")

# Tests that the function raises a ValueError when given a string with only numbers. 
def test_only_numbers():
    with pytest.raises(ValueError):
        parse_interface_name("12345")

# Tests that the function correctly extracts the interface type and ID from a valid Loopback interface name. 
def test_happy_path_loopback():
    result = parse_interface_name("Loopback0")
    assert result == ("Loopback", "0")

# Tests that the function raises a ValueError when given a string with only non-alphanumeric characters. 
def test_only_special_characters():
    with pytest.raises(ValueError):
        parse_interface_name("!@#$%")