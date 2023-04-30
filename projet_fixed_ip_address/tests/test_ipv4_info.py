import pytest
# importing sys
import sys
# adding Folder_2/subfolder to the system path
sys.path.insert(1, 'C:\git_folder\kostya-1\projet_fixed_ip_address')
from common import extract_ipv4_info



# Tests that the function correctly extracts all IPv4 information from a valid IPv4 address with prefix provided as input. 
def test_ipv4_info_extraction_valid_input():
    ipv4_info = extract_ipv4_info('192.168.1.0/24')
    assert ipv4_info['ip4_address'] == '192.168.1.0'
    assert ipv4_info['ip4_netmask'] == '255.255.255.0'
    assert ipv4_info['ip4_network'] == '192.168.1.0/24'
    assert ipv4_info['ip4_prefix'] == '24'
    assert ipv4_info['ip4_broadcast'] == '192.168.1.255'
    assert ipv4_info['ip4_gateway'] == '192.168.1.254'

# Tests that the function raises a ValueError if an invalid IPv4 address is provided as input. 
def test_ipv4_info_extraction_invalid_address():
    with pytest.raises(ValueError):
        extract_ipv4_info('invalid_ip_address')

# Tests that the function raises a ValueError if an invalid prefix length is provided as input. 
def test_ipv4_info_extraction_invalid_prefix():
    with pytest.raises(ValueError):
        extract_ipv4_info('192.168.1.1/33')

# Tests that the function correctly extracts the IPv4 information for different prefix lengths. 
def test_ipv4_info_extraction_different_prefix_lengths():
    ipv4_info = extract_ipv4_info('10.0.0.0/8')
    assert ipv4_info['ip4_prefix'] == '8'

    ipv4_info = extract_ipv4_info('172.16.0.0/12')
    assert ipv4_info['ip4_prefix'] == '12'

    ipv4_info = extract_ipv4_info('192.168.0.0/16')
    assert ipv4_info['ip4_prefix'] == '16'
