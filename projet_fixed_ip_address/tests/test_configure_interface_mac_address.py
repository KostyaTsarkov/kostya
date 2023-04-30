import pytest

# importing sys
import sys
# adding Folder_2/subfolder to the system path
sys.path.insert(1, '/Users/user/github/kostya-1/projet_fixed_ip_address')
from nb_ipam_api import *


# Tests that the function returns the configured MAC address when a valid MAC address is provided as input. 
def test_happy_path_valid_mac_address(self):
    assert configure_interface_mac_address("00:11:22:33:44:55") == "00:11:22:33:44:55"

# Tests that the function returns None when None is provided as input. 
def test_edge_case_none_input(self):
    assert configure_interface_mac_address(None) == None

# Tests that the function returns None when an empty string is provided as input. 
def test_edge_case_empty_string_input(self):
    assert configure_interface_mac_address("") == None

# Tests that the function prints the current value of mac_address. 
def test_general_behavior_print_mac_address(self, capsys):
    configure_interface_mac_address("00:11:22:33:44:55")
    captured = capsys.readouterr()
    assert "MAC address is 00:11:22:33:44:55..." in captured.out

# Tests that the function returns None when an invalid MAC address is provided as input. 
def test_edge_case_invalid_mac_address_input(self):
    assert configure_interface_mac_address("invalid_mac_address") == None

# Tests that the function returns None when an invalid MAC address is provided as input. 
def test_general_behavior_return_none(self):
    assert configure_interface_mac_address("invalid_mac_address") == None