import pytest

# importing sys
import sys
# adding Folder_2/subfolder to the system path
sys.path.insert(1, 'C:\git_folder\kostya-1\projet_fixed_ip_address')
from common import *


# Tests that the function correctly extracts IPv4 address, netmask, network, prefix, broadcast, and gateway from a valid IPv4 address input. 
def test_happy_path_valid_ipv4(mocker):
    # Arrange
    netbox_ip_address = '192.168.1.1/24'
    expected_result = {
        'ip4_address': '192.168.1.1',
        'ip4_netmask': '255.255.255.0',
        'ip4_network': '192.168.1.0/24',
        'ip4_prefix': '24',
        'ip4_broadcast': '192.168.1.255',
        'ip4_gateway': '192.168.1.254'
    }
    mocker.patch('builtins.logger.error')
    
    # Act
    result = configure_interface_ipv4_address(netbox_ip_address, 'dcim', 123)
    
    # Assert
    assert result == expected_result
    assert not logger.error.called

# Tests that the function logs an error message and calls the journal_template_fill function when an invalid IPv4 address is provided as input. 
def test_edge_case_invalid_ipv4(mocker):
    # Arrange
    netbox_ip_address = 'invalid_ip_address'
    expected_result = {}
    mocker.patch('builtins.logger.error')
    mocker.patch('journal_template_fill')
    
    # Act
    result = configure_interface_ipv4_address(netbox_ip_address, 'dcim', 123)
    
    # Assert
    assert result == expected_result
    assert logger.error.called
    assert journal_template_fill.called

# Tests that the function returns an empty dictionary when no input is provided. 
def test_general_behavior_missing_input(self, mocker):
    # Arrange
    expected_result = {}
    mocker.patch('builtins.logger.error')
    
    # Act
    result = configure_interface_ipv4_address()
    
    # Assert
    assert result == expected_result
    assert not logger.error.called

# Tests that the function returns a dictionary with extracted information when no global_dcim parameter is provided. 
def test_general_behavior_missing_global_dcim(self, mocker):
    # Arrange
    netbox_ip_address = '192.168.1.1/24'
    expected_result = {
        'ip4_address': '192.168.1.1',
        'ip4_netmask': '255.255.255.0',
        'ip4_network': '192.168.1.0/24',
        'ip4_prefix': '24',
        'ip4_broadcast': '192.168.1.255',
        'ip4_gateway': '192.168.1.254'
    }
    mocker.patch('builtins.logger.error')
    
    # Act
    result = configure_interface_ipv4_address(netbox_ip_address, global_id=123)
    
    # Assert
    assert result == expected_result
    assert not logger.error.called

# Tests that the function returns a dictionary with extracted information when no global_id parameter is provided. 
def test_general_behavior_missing_global_id(self, mocker):
    # Arrange
    netbox_ip_address = '192.168.1.1/24'
    expected_result = {
        'ip4_address': '192.168.1.1',
        'ip4_netmask': '255.255.255.0',
        'ip4_network': '192.168.1.0/24',
        'ip4_prefix': '24',
        'ip4_broadcast': '192.168.1.255',
        'ip4_gateway': '192.168.1.254'
    }
    mocker.patch('builtins.logger.error')
    
    # Act
    result = configure_interface_ipv4_address(netbox_ip_address, global_dcim='dcim')
    
    # Assert
    assert result == expected_result
    assert not logger.error.called

# Tests that the function returns an empty dictionary when no global_dcim and global_id parameters are provided. 
def test_general_behavior_missing_global_parameters(self, mocker):
    # Arrange
    expected_result = {}
    mocker.patch('builtins.logger.error')
    
    # Act
    result = configure_interface_ipv4_address()
    
    # Assert
    assert result == expected_result
    assert not logger.error.called