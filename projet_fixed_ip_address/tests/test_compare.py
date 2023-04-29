import pytest
# importing sys
import sys
# adding Folder_2/subfolder to the system path
sys.path.insert(1, 'C:\git_folder\kostya-1\projet_fixed_ip_address')
from common import *


# Tests that the function returns None when comparing two identical dictionaries. 
def test_compare_identical_dicts():
    old_dict = {'key1': 'value1', 'key2': 'value2'}
    new_dict = {'key1': 'value1', 'key2': 'value2'}
    assert compare(old_dict, new_dict) is None

# Tests that the function correctly compares two dictionaries with only one key-value pair. 
def test_compare_single_key():
    print("test_compare_single_key")
    old_dict = {'key1': 'value1'}
    new_dict = {'key1': 'value2'}
    expected_diffs = {'key1': {'old_value': 'value1', 'new_value': 'value2'}}
    actual_diffs = compare(old_dict, new_dict)
    # Sort the dictionaries by keys before comparing them
    expected_diffs_sorted = dict(sorted(expected_diffs.items()))
    actual_diffs_sorted = dict(sorted(actual_diffs.items()))
    assert expected_diffs_sorted == actual_diffs_sorted


# Tests that the function raises a TypeError if either input is not a dictionary. 
def test_compare_non_dict_input():
    with pytest.raises(TypeError):
        compare('not a dict', {'key': 'value'})

# Tests that the function returns None when comparing two empty dictionaries. 
def test_compare_empty_dicts():
    assert compare({}, {}) is None

# Tests that the function correctly handles nested dictionaries with different structures. 
def test_compare_different_nested_dicts():
    old_dict = {'key1': {'nested_key1': 'value1'}}
    new_dict = {'key1': {'nested_key2': 'value2'}}
    expected_diffs = {'key1.nested_key1': {'old_value': 'value1', 'new_value': None},
                        'key1.nested_key2': {'old_value': None, 'new_value': 'value2'}}
    assert compare(old_dict, new_dict) == expected_diffs

# Tests that the function correctly compares two nested dictionaries with identical values. 
def test_compare_nested_dicts():
    old_dict = {'key1': {'nested_key1': 'value1'}}
    new_dict = {'key1': {'nested_key1': 'value1'}}
    assert compare(old_dict, new_dict) is None