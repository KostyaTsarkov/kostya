from logging import Logger
from typing import Any, Dict, List, Optional, Union
from nornir.core import Nornir
from journal import journal_template_fill
import ipaddress
import re
from deepdiff import DeepDiff
from global_var import templates_path
from flask import request, Response
from config import netbox_api
from types import SimpleNamespace
import time
from multiping import multi_ping
from nornir import InitNornir
from credentials import (netbox_url, netbox_token)
from jinja2 import Environment, FileSystemLoader, TemplateError
from nornir_napalm.plugins.tasks import napalm_get
from nornir_netmiko.tasks import netmiko_send_config


def parse_interface_name(interface_name: str) -> tuple:
    """
    Parses an interface name string into its type and ID components.

    Args:
        interface_name: A string representing the name of the interface
        to parse.

    Returns:
        A tuple containing two strings: the type of the interface and its ID.

    Raises:
        ValueError: If the interface name is invalid and cannot be parsed.
    """
    # Define a regular expression pattern to match the interface name
    # The pattern consists of two groups:
    #   1. A non-digit character sequence to capture the interface type
    #   2. A digit sequence followed by any characters to capture
    #      the interface ID
    INTERFACE_PATTERN = r"^(\D+)(\d+.*)$"

    # Compile the regular expression pattern into a regex object
    interface_regex = re.compile(INTERFACE_PATTERN)

    try:
        # Attempt to extract the interface type and ID using the regex
        interface_type, interface_id = interface_regex.fullmatch(
            interface_name).groups()  # type: ignore
    except AttributeError:
        # If the regex doesn't match, the interface name is invalid
        raise ValueError("Invalid interface name")

    # Return the interface type and ID as a tuple
    return interface_type, interface_id


# Define a function called 'extract_ipv4_info' which takes
# a string argument 'netbox_ip_address' and returns a dictionary
def extract_ipv4_info(netbox_ip_address: str) -> dict:
    """
    Extracts IPv4 address, netmask, network, prefix, broadcast,
    and gateway from a given IP address

    Args:
        netbox_ip_address (str): IPv4 address (IP/Prefix)

    Returns:
        dict: A dictionary containing the extracted IPv4 address, netmask,
        network, prefix, broadcast, and gateway
    """
    # Convert the given IP address to CIDR notation
    ip_cidr = ipaddress.ip_interface(netbox_ip_address)

    # Initialize an empty dictionary called 'ipv4_dict' to store
    # the extracted information
    ipv4_dict = {}

    # Extract the IPv4 address and add it to the dictionary
    ipv4_dict['ip4_address'] = str(ipaddress.IPv4Interface(
        ip_cidr).ip)

    # Extract the IPv4 netmask and add it to the dictionary
    ipv4_dict['ip4_netmask'] = str(ipaddress.IPv4Interface(
        ip_cidr).netmask)

    # Extract the IPv4 network address and add it to the dictionary
    ipv4_dict['ip4_network'] = str(ipaddress.IPv4Interface(
        ip_cidr).network)

    # Extract the IPv4 prefix length and add it to the dictionary
    ipv4_dict['ip4_prefix'] = str(ipaddress.IPv4Network(
        ipv4_dict['ip4_network']).prefixlen)

    # Extract the IPv4 broadcast address and add it to the dictionary
    ipv4_dict['ip4_broadcast'] = str(ipaddress.IPv4Network(
        ipv4_dict['ip4_network']).broadcast_address)

    # If the IPv4 network has more than one address,
    # extract the IPv4 gateway address and add it to the dictionary
    if ipaddress.IPv4Network(ipv4_dict['ip4_network']).num_addresses > 1:
        ipv4_dict['ip4_gateway'] = str(list(ipaddress.IPv4Network(
            ipv4_dict['ip4_network']).hosts())[-1])

    # Return the dictionary containing the extracted information
    return ipv4_dict


# This function configures an IPv4 address for an interface using data
# from Netbox.
# It takes in a netbox_ip_address in string format (e.g. 192.0.2.1/24)
# and global_dcim, global_id objects.
# It returns a dictionary containing the extracted IP address, subnet mask,
# and broadcast address.
def configure_interface_ipv4_address(netbox_ip_address: str = '0.0.0.0',
                                     global_dcim=None, global_id=None) -> dict:
    """
    Configures an IPv4 address for an interface using data from Netbox.

    Args:
        netbox_ip_address (str): The IP address in Netbox format
        (e.g. 192.0.2.1/24).
        global_dcim: The global DCIM object.
        global_id: The global ID object.

    Returns:
        ipv4_dict (dict): A dictionary containing the extracted IP address,
        subnet mask, and broadcast address.
    """
    # Create an empty dictionary to store the extracted IP address,
    # subnet mask, and broadcast address.
    ipv4_dict = {}

    try:
        # Call a function to extract the IP address, subnet mask,
        # and broadcast address from the netbox_ip_address.
        ipv4_dict = extract_ipv4_info(netbox_ip_address)

    except ipaddress.AddressValueError:
        # If the netbox_ip_address is invalid, log an error and add
        # a journal entry.
        comment = f'Invalid address/netmask for IPv4 {netbox_ip_address}'
        level = 'error'
        journal_template_fill(comment,
                              level,
                              global_id,
                              global_dcim)
        Logger.error(comment)

    # Return the dictionary containing the extracted IP address, subnet mask,
    # and broadcast address.
    return ipv4_dict


def get_management_address(device_interface: Any) -> Union[str, None]:
    """
    This function takes a device interface object and returns the IP address
    of the device's primary interface,
    which can be used as the management address. If the device_interface
    object or its attributes are None, None is returned.

    Args:
        device_interface (Any): A device interface object.

    Returns:
        Union[str, None]: The IP address of the device's primary interface,
        or None if the device_interface object or its attributes are None.
    """
    # Check if the device_interface object or its name attribute are None,
    # and return None if so
    if not device_interface or not device_interface.name:
        return None

    # Parse the interface name to determine its type and ID
    interface_type, interface_id = parse_interface_name(device_interface.name)

    # Check if the device_interface object or its device attribute or
    # its primary_ip attribute are None, and return None if so
    if not device_interface.device or not device_interface.device.primary_ip:
        return None

    # Get the primary IP address of the device
    primary_ip = device_interface.device.primary_ip

    # Try to configure the interface's IPv4 address using the primary
    # IP address, and return the IP address if successful.
    # If an error occurs (e.g. the primary IP address is invalid),
    # return None
    try:
        return configure_interface_ipv4_address(primary_ip)['ip4_address']
    except (KeyError, TypeError):
        return None


def compare(prechange, postchange):
    """
    Compare two dictionaries and return a dictionary of the differences
    between them.

    Args:
        prechange (Dict[str, Union[str, int, float]]): The first dictionary
        to compare.
        postchange (Dict[str, Union[str, int, float]]): The second dictionary
        to compare.
        exclude_paths (Optional[str], optional): Exclude a specific key from
        the comparison. Defaults to "root['last_updated']".

    Returns:
        Optional[Dict[str, Union[str, int, float]]]: A dictionary of
        the differences between the two input dictionaries.
    """
    # Compare the two dictionaries using the DeepDiff library
    compare = DeepDiff(prechange,
                       postchange,
                       exclude_paths="root['last_updated']")

    # Initialize an empty dictionary and two empty lists
    change = {}
    change_key = []
    new_value = []

    # Loop through the keys in the 'compare' dictionary
    for key in compare.keys():
        # If the key is 'values_changed' or 'type_changes'
        if key == 'values_changed' or key == 'type_changes':
            # Loop through the keys in the 'values_changed' or 'type_changes'
            # dictionary
            for inkey in compare[key].keys():
                # Extract the key name from the string using regex and append
                # it to the 'change_key' list
                change_key.append(re.findall("'([^']*)'", inkey)[0])
                # Append the new value to the 'new_value' list
                new_value.append(compare[key][inkey]['new_value'])

    # Combine the 'change_key' and 'new_value' lists into a dictionary
    change = dict(zip(change_key, new_value))

    # If there are no changes, set 'change' to None
    if len(change) == 0:
        change = None

    # Return the 'change' dictionary
    return change


# This function takes in a variable called 'data'
def convert_none_to_str(value: str or None) -> str:
    """
    Convert None to an empty string.

    Args:
        value: Any data type.

    Returns:
        A string representing the input value,
        or an empty string if the input is None.
    """
    return str(value) if value is not None else ''


def create_nornir_session(netbox_url: str,
                          netbox_token: str) -> Optional[Nornir]:
    """
    Creates a Nornir object using the NetBoxInventory2 plugin.

    Args:
        netbox_url (str): The URL of the NetBox instance.
        netbox_token (str): The API token to authenticate with NetBox.

    Returns:
        Optional[Nornir]: The created Nornir object,
        or None if an error occurred.

    Raises:
        TypeError: If netbox_url or netbox_token is not a string.
        ValueError: If netbox_url does not start with 'http' or 'https'.
    """
    # Ensure that the arguments are strings
    if not isinstance(netbox_url, str) or not isinstance(netbox_token, str):
        raise TypeError("netbox_url and netbox_token must be strings")

    # Ensure that the netbox_url argument starts with 'http' or 'https'
    if not netbox_url.startswith(("http", "https")):
        raise ValueError("netbox_url must start with 'http' or 'https'")

    # Define inventory options
    inventory = {
        "plugin": "NetBoxInventory2",
        "options": {
            "nb_url": netbox_url,
            "nb_token": netbox_token,
            "group_file": "./inventory/groups.yml",
            "defaults_file": "./inventory/defaults.yml",
        },
    }

    # Try to create a Nornir object using the Netmiko plugin
    try:
        nornir = InitNornir(inventory=inventory)
    except Exception as e:
        # If the creation of the Nornir object fails, print an error message
        print(f"Error creating Nornir object: {e}")
        return None

    # Return the created Nornir object
    return nornir


# This function generates a Cisco IOS configuration for a given interface
# based on a set of templates. It takes in an interface object and an event
# (optional), which can be used to control what template gets used.
def get_cisco_interface_config(interface, event='None'):
    """
    Fills a Cisco IOS configuration template with data from
    an interface object.

    Args:
        interface (Interface): An object representing the interface
        to configure.
        event (str): Optional event type that determines which template to use.
            Default is 'None'.

    Returns:
        str: The content of the filled template.
    """
    # Define global variables for the DCIM device and device ID
    global global_id, global_dcim
    global_dcim = 'dcim.device'
    global_id = interface.device.id

    # This is a nested function that fills a given template with a set of
    # arguments and returns the content. It uses the Jinja2 templating engine.
    def fill_template(*args: Any, **kwargs: str) -> Optional[str]:
        """
        This function takes in a Jinja2 template file and
        fills it with the given arguments.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Keyword Args:
            template_file (str): The filename of the Jinja2 template
                to be used.

        Returns:
            Optional[str]: The rendered template content, or None
            if there was not enough data to fill out the template.
        """
        # Set up a Jinja2 environment with a template loader
        environment = Environment(loader=FileSystemLoader(templates_path))

        # Get the template file from the kwargs
        template = environment.get_template(kwargs['template_file'])

        # Initialize the content to None
        content = None

        # Try to render the template with the given arguments
        try:
            if event == 'shutdown':
                # If the event is 'shutdown', only pass in the interface name
                content = template.render(interface_name=convert_none_to_str(
                    interface.name))
            else:
                # Otherwise, pass in the interface name, description, VLAN,
                # and mode
                content = template.render(
                    interface_name=convert_none_to_str(interface.name),
                    descr=convert_none_to_str(interface.description),
                    access_vlan=convert_none_to_str(interface.untagged_vlan.vid),
                    mode=convert_none_to_str(interface.mode.value))
        except TemplateError:
            # If there's not enough data to fill out the template,
            # log a warning and return None
            comment = 'Not enough data to fill out the template'
            level = 'warning'
            print(journal_template_fill(comment, level, global_id, global_dcim))
        else:
            # Otherwise, log that the template is being filled
            # and return the content
            print("Filling in the template...")

        return content

    # Determine which template file to use based on the event
    if event == 'shutdown':
        template_file = "cisco_ios_shutdown_interface.template"
    elif event != 'delete':
        template_file = "cisco_ios_access_interface.template"
    else:
        template_file = "cisco_ios_default_interface.template"

    # Fill the template and return the content
    content = fill_template(interface=interface,
                            template_file=template_file,
                            event=event)
    return content


def push_interface_config(netbox_interface, content: str, 
                          event: str = 'None') -> None:
    """
    Pushes configuration to a network interface.

    Parameters:
        netbox_interface (Interface): the Netbox interface object
        to be configured
        content (str): the configuration content to be pushed
        event (str): not used in the function, just for compatibility
        with an external system

    Returns:
        None
    """
    # Define global variables used in the function
    global global_id, global_dcim, config_context

    global_dcim = 'dcim.device'
    # Get the ID of the device associated with the interface
    global_id = netbox_interface.device.id
    # Get the role of the device associated with the interface
    device_role = netbox_interface.device.device_role.slug
    # Get the name of the device associated with the interface
    device_name = netbox_interface.device.name
    # Get the list of device roles allowed in the configuration context
    network_devices_roles = config_context.network_devices_roles

    # Check that the device role is allowed in the configuration context
    if device_role in network_devices_roles:
        # Get the number of connection attempts allowed
        attempts = config_context.attempts
        # Get the time to wait between connection attempts
        attempt_timeout = config_context.attempt_timeout
        # Initialize the number of failed connection attempts to 0
        fail_count = config_context.fail_count
        # Get the name of the interface to configure
        name = netbox_interface.name
        addrs = []
        # Get the management address of the interface
        filter_query = get_management_address(netbox_interface)
        addrs.append(filter_query)

        # Ping the management address to check if it's available
        responses, no_responses = multi_ping(addrs,
                                             timeout=config_context.timeout,
                                             retry=config_context.retry,
                                             ignore_lookup_errors=config_context.ignore_lookup_errors)
        print("icmp ping...")

        # If the management address is available
        if filter_query in list(responses.keys()):
            print('{} is available...'.format(addrs))
            # Create a Nornir session
            nr = create_nornir_session(netbox_url, netbox_token)
            if nr is None:
                print('Could not connect to device...')
                print('{}'.format(no_responses))
            else:
                with nr:
                    # Filter the Nornir session to only include the device with the management address
                    with nr.filter(hostname=filter_query) as sw:
                        # Set the device's username to the one in the configuration context
                        sw.inventory.hosts[device_name].username = config_context.device_username
                        # Set the device's password to the one in the configuration context
                        sw.inventory.hosts[device_name].password = config_context.device_password

                        # Get all interfaces on the device
                        get_int = sw.run(task=napalm_get, getters=['get_interfaces'])

                        # Try to connect to the device
                        for _ in range(attempts):
                            print('Attempting to connect {}...'.format(_ + 1))

                            # If the connection fails
                            if get_int.failed is True:
                                fail_count += 1
                                time.sleep(attempt_timeout)

                            # If the connection is successful
                            else:
                                print('Connection state is connected...')

                                for device in get_int.values():
                                    # Get the interfaces as keys in a dictionary
                                    interfaces = device.result['get_interfaces'].keys()
                                    if name in (intf for intf in list(interfaces)):
                                        print("Find {} for device {}...".format(name, device.host))
                                        result = sw.run(netmiko_send_config, name="Configuration interface.../",
                                                        config_commands=content)
                                        # Add an entry to the journal
                                        comment = 'All operations are performed'
                                        level = 'success'
                                        print(journal_template_fill(comment, level, global_id, global_dcim))

                                break
                        if fail_count >= attempts:
                            # Add an entry to the journal
                            comment = 'All operations are performed'
                            level = 'error'
                            print(journal_template_fill(comment, level, global_id, global_dcim))
                            # <
                sw.close_connections()
                print("Connection state is closed.")

        elif filter_query in no_responses:
            # Add an entry to the journal
            comment = '{} is not available'.format(addrs)
            level = 'warning'
            print(journal_template_fill(comment, level, global_id, global_dcim))
    else:
        # Add an entry to the journal
        comment = 'Devices must match the list of {}'.format(network_devices_roles)
        level = 'notification'
        print(journal_template_fill(comment, level, global_id, global_dcim))


def change_config_intf(netbox_interface, event: str) -> None:
    """
    Changes the connection (cable) in Netbox, 
    leaving the switch port settings unchanged.

    Args:
        netbox_interface (pynetbox.models.dcim.interfaces.Interface):
            Reference to the interface object in pynetbox.
        event (str): The type of event that triggered the function.
            Can be 'shutdown', 'delete', 'update', or 'create'.

    Returns:
        None
    """
    interface_name = netbox_interface.name
    # Define global variables used in the function
    global global_id, global_dcim

    try:
        content = get_cisco_interface_config(netbox_interface, event)
        if content is not None:
            # Join the list of strings into a single string
            content = '\n'.join(content)
            print(f"{event.capitalize()} interface {netbox_interface} config...")
            push_interface_config(netbox_interface, content, event)
        else:
            print("No data returned from cisco_config_interface()")
    except Exception:
        # Add an entry to the journal
        comment = f"No data for {event.lower()} {interface_name}"
        level = 'informational'
        print(journal_template_fill(comment, level, global_id, global_dcim))


def manage_connected_interfaces(intf: Dict[str, Any], event: str,
                                role: str) -> None:
    """
    Manage connected interfaces in NetBox

    Args:
        intf (Dict[str, Any]): The interface to manage
        event (str): The event that triggered this function
                     (create, update, or delete)
        role (str): The role of the device to which the interface belongs

    Returns:
        None
    """
    # Define global variables used in the functions
    global global_id, global_dcim, config_context

    # Get device roles from config_context
    network_device_roles = config_context.network_devices_roles
    user_device_roles = config_context.user_devices_roles

    # Define a helper function that creates a dictionary of changes
    # to be made to the interface
    def create_changes_dict(network_device_id: int, user_intf: Dict[Any, Any]) -> List[Dict[Any, Union[Any, Any]]]:
        """
        Create a dictionary of changes to be made to the interface

        Args:
            network_device_id (int): The ID of the neighboring device
            user_intf (Dict[Any, Any]): The interface to update

        Returns:
            List[Dict[Any, Union[Any, Any]]]: A list of dictionaries 
            representing the changes to be made
        """
        changes = {}
        change_key = ['id']
        # add the neighboring device's ID as the key
        new_value = [network_device_id]
        # Loop through the user_intf and add any values that exist in
        # the predefined list and are not empty
        for value in user_intf:
            if value[0] in config_context.interface and value[1] not in ['', None]:
                change_key.append(value[0])
                # If the value is a dictionary, convert it to a list
                if isinstance(value[1], dict):
                    new_value.append(list(value[1].values())[0])
                else:
                    new_value.append(value[1])
        changes = dict(zip(change_key, new_value))
        return [changes]

    # If the role is a user device and the event is not 'delete'
    if role in user_device_roles and event != 'delete':
        # Check if the interface is connected to another device
        if intf['connected_endpoints_reachable']:
            # Get the neighboring device's ID
            network_device_id = intf['connected_endpoints'][0]['id']
            # Create a dictionary of changes to be made to the interface
            changes = create_changes_dict(network_device_id, intf)
            # Update the interface data via netbox_api
            netbox_api.dcim.interfaces.update(changes)
        else:
            # If the interface is not connected to another device,
            # add a log entry
            comment = f"Neighbor is not reachable for {intf}"
            level = 'notification'
            print(journal_template_fill(comment, level, global_id, global_dcim))

    # If the role is a network device and the event is not 'delete'
    elif role in network_device_roles and event != 'delete':
        # Check if the interface is connected to another device
        if intf['connected_endpoints_reachable']:
            # Get the neighboring device's interface
            network_intf = netbox_api.dcim.interfaces.get(intf['connected_endpoints'][0]['id'])
            # Get the ID of the network device
            network_device_id = intf.id  # type: ignore
            # Create a dictionary of changes to be made to the interface
            if network_intf and network_device_id:
                changes = create_changes_dict(network_device_id, network_intf)
                # Update the interface data via netbox_api
                netbox_api.dcim.interfaces.update(changes)
        else:
            # If the interface is not connected to another device,
            # add a log entry
            comment = f"Neighbor is not reachable for {intf}"
            level = 'notification'
            print(journal_template_fill(comment, level, global_id, global_dcim))

    # If the role is a network device and the event is 'delete'
    elif role in network_device_roles and event == 'delete':
        # Create a dictionary of changes to be made to the interface
        changes = dict.fromkeys(config_context.interface, None)
        changes['description'] = ""
        changes['id'] = intf.id  # type: ignore
        changes['enabled'] = False
        # Update the interface data via netbox_api
        netbox_api.dcim.interfaces.update([changes])
        print(f"Clear {intf} netbox interface config")


def mng_cable() -> Response:
    """
    Receives a POST json with the keys 'data' and 'event' containing
    information about a cable connection.
    Verifies that the connection is point-to-point between
    interfaces (Interface).
    Verifies that the connected devices correspond to
    a list of pre-defined roles.
    Modifies the configuration of the interface if necessary.
    Returns a Response(status=204).

    Args:
        request (flask.request): The request object containing
        the POST json data.

    Returns:
        Response: HTTP response object with status code 204.
    """
    try:
        # List of keys for the 'devices' dictionary
        device_keys = ['role','device_id','intf_id']

        # List of dictionaries that will hold data for each device
        devices = []

        # List of device names
        device_names = []

        # List of roles for each device
        device_roles = []

        # Regular expression pattern for termination names
        TERMINATIONS_REGEX = "[a|b]_terminations"

        device_intf_id = int

        # Get data from webhook sent by Netbox via Flask
        if request.json:
            # Cable data
            cable_data = request.json['data']
            # Type of event
            event_type = request.json["event"]
            # Snapshot of data before change
            pre_change_snapshot = request.json['snapshots']['prechange']
            # Snapshot of data after change
            post_change_snapshot = request.json['snapshots']['postchange']

            # Define global variables used in the functions
            global global_id, global_dcim, config_context
            global_dcim = 'dcim.cable'
            global_id = int(cable_data['id'])

            for cable_key in cable_data.keys():
                if re.match(TERMINATIONS_REGEX, cable_key) and len(cable_data[cable_key]) == 1:
                    for i in range(len(cable_data[cable_key])):
                        device_id = cable_data[cable_key][i]['object']['device']['id']
                        device_values = []
                        device_names.append(
                            netbox_api.dcim.devices.get(
                                device_id).name)  # type: ignore
                        device_values.append(
                            netbox_api.dcim.devices.get(
                                device_id).device_role.slug)  # type: ignore
                        device_values.append(
                            device_id)
                        device_values.append(
                            cable_data[cable_key][i]['object']['id'])
                        devices.append(dict(zip(device_keys, device_values)))

            config_context = SimpleNamespace(**dict(
                netbox_api.dcim.devices.get(
                    device_id).config_context))  # type: ignore
            roles = config_context.network_devices_roles
            roles.extend(config_context.user_devices_roles)

            for device in devices:
                device_roles.append(device['role'])

            print(f"{event_type.upper()} cable ID #{cable_data['id']} between {device_names}...")  # type: ignore

            # Check if device roles are a subset of template roles
            if set(device_roles).issubset(set(roles)):
                # Iterate over devices
                for device in devices:
                    # Check if the device role matches the first template role
                    if device['role'] == roles[0]:
                        # Get the interface ID of the device
                        device_intf_id = device['intf_id']

                # Get the interface object from the Netbox API using the interface ID

                get_device_interface = netbox_api.dcim.interfaces.get(device_intf_id)

                # Get interface name and mode, as well as device ID
                interface_name = convert_none_to_str(
                    get_device_interface.name if get_device_interface.name else None)  # type: ignore
                interface_mode_802_1Q = convert_none_to_str(
                    get_device_interface.mode.value if get_device_interface.mode else None)  # type: ignore
                global_dcim = 'dcim.device'
                global_id = get_device_interface.device.id  # type: ignore

                # Create a namespace from the device's config context
                config_context = SimpleNamespace(**dict(netbox_api.dcim.devices.get(global_id).config_context))  # type: ignore

                # Print a message indicating the connection between the two devices
                print(f"Connection between {device_roles[0]} and {device_roles[1]}, switch access interface ID: {device_intf_id}...")

                # Check if the interface is a management interface
                if get_device_interface.mgmt_only:  # type: ignore
                    # Add notification to the journal
                    comment = '{} is management interface, no changes will be performed'.format(interface_name)
                    level = 'notification'
                    print(journal_template_fill(comment, level, global_id, global_dcim))

                # Check if the interface mode is tagged or tagged-all
                elif interface_mode_802_1Q in ['tagged', 'tagged-all']:
                    # Call a function to modify device port settings
                    print('Interface {} is mode {}'.format(interface_name, interface_mode_802_1Q))

                else:
                    # Determine the type of event that triggered this code block
                    if event_type == "created" and get_device_interface is not None:
                        # Call a function to manage connected interfaces when an interface is created
                        manage_connected_interfaces(get_device_interface, event='create', role=roles[0])
                    elif event_type == "deleted" and get_device_interface is not None:
                        # Call a function to manage connected interfaces when an interface is deleted
                        manage_connected_interfaces(get_device_interface, event='delete', role=roles[0])
                    elif get_device_interface.enabled == False: # type: ignore
                        # Print a message indicating that the interface was turned off before
                        print('Interface {} was turned off before'.format(interface_name))
                        pass
                    elif event_type == "updated" and compare(pre_change_snapshot, post_change_snapshot) is not None:
                        # Call a function to change the device interface configuration
                        change_config_intf(netbox_interface=get_device_interface, event='update')
                    else:
                        # Add informational message to the journal
                        comment = 'No data for {} {}'.format(event_type.lower(), interface_name)
                        level = 'informational'
                        print(journal_template_fill(comment, level, global_id, global_dcim))
            # If device roles are not a subset of template roles
            else:
                # Add notification to the journal
                comment = 'Devices must match the list of {}'.format(roles)
                level = 'notification'
                print(comment)
    # Catch any errors that occur during execution
    except ValueError:
        print('Something went wrong!')
    except KeyError:
        print('Something went wrong!')
    # Return a 204 (No Content) response to the webhook
    finally:
        return Response(status=204)


# Define a function that handles incoming POST requests from
# a NetBox webhook
def mng_int() -> Response:
    """
    Receives a webhook from NetBox via Flask and
    performs actions based on the data.

    Returns:
        A 204 (No Content) response to the webhook.
    """
    try:
        # Get data from the webhook sent by NetBox via Flask
        if request.json:
            # Extract relevant information from the JSON data
            data = request.json['data']
            event_type = request.json['event']
            pre_change_snapshot = request.json['snapshots']['prechange']
            post_change_snapshot = request.json['snapshots']['postchange']

            # Get interface data from NetBox API
            intf_id = data['id']
            intf = netbox_api.dcim.interfaces.get(intf_id)
            intf_name = convert_none_to_str(intf.name)  # type: ignore
            device_role = convert_none_to_str(intf.device.device_role.slug)  # type: ignore
            intf_mode_802_1Q = convert_none_to_str(intf.mode.value if intf.mode else None)  # type: ignore

            # Define global variables used in the function
            global global_id, global_dcim, config_context
            global_dcim = 'dcim.device'
            global_id = intf.device.id # type: ignore
            config_context = SimpleNamespace(**dict(netbox_api.dcim.devices.get(global_id).config_context))
            network_devices_roles = convert_none_to_str(config_context.network_devices_roles)
            user_devices_roles = convert_none_to_str(config_context.user_devices_roles)

            # Print out the event type and interface name
            print("{} {}...".format(event_type.upper(), intf_name))

            # Check if interface is a management interface
            if intf.mgmt_only:  # type: ignore
                comment = '{} is management interface, no changes will be performed'.format(intf_name)
                level = 'notification'
                print(journal_template_fill(comment, level, global_id, global_dcim))

            # Check if data has changed
            elif compare(pre_change_snapshot, post_change_snapshot) is None:
                comment = 'No data for {} {}'.format(event_type.lower(), intf_name)
                level = 'informational'
                print(journal_template_fill(comment, level, global_id, global_dcim))
            # Check if the change is from disabled to disabled
            elif data['enabled'] is False and pre_change_snapshot['enabled'] is False:
                print('Interface {} was turned off before'.format(intf_name))
            # Check if device is a network device
            elif device_role in network_devices_roles:
                # Check if interface is a trunk
                if intf_mode_802_1Q in ['tagged', 'tagged-all']:
                    print('Interface {} is mode {}'.format(intf_name, intf_mode_802_1Q))
                    change_config_intf(intf, event='update')
                else:   
                    # Check if the change is from enabled to disabled
                    if data['enabled'] is False and pre_change_snapshot['enabled'] is True:
                        comment = 'Interface {} is disabled on the device'.format(intf_name)
                        level = 'notification'
                        print(journal_template_fill(comment, level, global_id, global_dcim))
                        change_config_intf(intf, event='shutdown')
                    else:
                        change_config_intf(intf, event='update')
            # Check if device is a user device
            elif device_role in user_devices_roles and intf is not None:
                manage_connected_interfaces(intf, event='update', role=device_role)
            else:
                print('Device role is "{}"'.format(device_role))
    # Catch any errors that occur during execution
    except ValueError:
        print('Something went wrong!')
    except KeyError:
        print('Something went wrong!')
    # Return a 204 (No Content) response to the webhook
    finally:
        return Response(status=204)
