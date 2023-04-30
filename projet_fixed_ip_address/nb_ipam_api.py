
from typing import Dict, Any, Optional
from flask import request, Response
from config import netbox_api
import ipaddress
from jinja2 import Environment, FileSystemLoader
from macaddress import MAC
from pydhcpdparser import parser
from global_var import( parent_path,
                        templates_path,
                        logger)



# Define a function called 'extract_ipv4_info' which takes a string argument 'netbox_ip_address' and returns a dictionary
def extract_ipv4_info(netbox_ip_address: str) -> dict:
    """
    Extracts IPv4 address, netmask, network, prefix, broadcast, and gateway from a given IP address
   
    Args:
        netbox_ip_address (str): IPv4 address (IP/Prefix)
   
    Returns:
        dict: A dictionary containing the extracted IPv4 address, netmask, network, prefix, broadcast, and gateway
    """    


    # Convert the given IP address to CIDR notation
    ip_cidr = ipaddress.ip_interface(netbox_ip_address)

    # Initialize an empty dictionary called 'ipv4_dic' to store the extracted information
    ipv4_dic = dict()

    # Extract the IPv4 address and add it to the dictionary
    ipv4_dic['ip4_address'] = f"{ipaddress.IPv4Interface(ip_cidr).ip}"

    # Extract the IPv4 netmask and add it to the dictionary
    ipv4_dic['ip4_netmask'] = f"{ipaddress.IPv4Interface(ip_cidr).netmask}"

    # Extract the IPv4 network address and add it to the dictionary
    ipv4_dic['ip4_network'] = f"{ipaddress.IPv4Interface(ip_cidr).network}"

    # Extract the IPv4 prefix length and add it to the dictionary
    ipv4_dic['ip4_prefix'] = f"{ipaddress.IPv4Network(ipv4_dic['ip4_network']).prefixlen}"

    # Extract the IPv4 broadcast address and add it to the dictionary
    ipv4_dic['ip4_broadcast'] = f"{ipaddress.IPv4Network(ipv4_dic['ip4_network']).broadcast_address}"

    # If the IPv4 network has more than one address, extract the IPv4 gateway address and add it to the dictionary
    if (ipaddress.IPv4Network(ipv4_dic['ip4_network']).num_addresses) > 1:
        ipv4_dic['ip4_gateway'] = f"{list(ipaddress.IPv4Network(ipv4_dic['ip4_network']).hosts())[-1]}"

    # Return the dictionary containing the extracted information
    return ipv4_dic
    
    
# This function configures an IPv4 address for an interface using data from Netbox.
# It takes in a netbox_ip_address in string format (e.g. 192.0.2.1/24) and global_dcim, global_id objects.
# It returns a dictionary containing the extracted IP address, subnet mask, and broadcast address.
def configure_interface_ipv4_address(netbox_ip_address: str = '0.0.0.0',global_dcim=None, global_id=None) -> dict:
    """
    Configures an IPv4 address for an interface using data from Netbox.

    Args:
        netbox_ip_address (str): The IP address in Netbox format (e.g. 192.0.2.1/24).
        global_dcim: The global DCIM object.
        global_id: The global ID object.

    Returns:
        ipv4_dict (dict): A dictionary containing the extracted IP address, subnet mask,
                          and broadcast address.

    """
    
    
    # Create an empty dictionary to store the extracted IP address, subnet mask, and broadcast address.
    ipv4_dict = {}

    try:
        # Call a function to extract the IP address, subnet mask, and broadcast address from the netbox_ip_address.
        ipv4_dict = extract_ipv4_info(netbox_ip_address)

    # If the netbox_ip_address is invalid, log an error and add a journal entry.
    except ipaddress.AddressValueError:
        comment, level = f'Invalid address/netmask for IPv4 {netbox_ip_address}', 'error'
        #journal_template_fill(comment, level, global_id, global_dcim)
        logger.error(comment)

    # Return the dictionary containing the extracted IP address, subnet mask, and broadcast address.
    return ipv4_dict


def configure_interface_mac_address(mac_address: Optional[str]) -> Optional[str]:
    """
    Configures the MAC address of an interface.

    Args:
        mac_address (Optional[str]): The MAC address to be configured.

    Returns:
        Optional[str]: The configured MAC address, or None if the input is not a valid MAC address.
    """
    
    
    # If mac_address is None, assign an empty string to it
    mac_address = '' if mac_address is None else mac_address

    try:
        # Check if the given MAC address is valid
        MAC(mac_address)
    except ValueError:
        # If the given MAC address is not valid, set mac_address to None
        mac_address = None

    # Print the current value of mac_address
    print(f"MAC address is {mac_address}...")

    # Return the configured MAC address
    return mac_address


def delete_config_file(device_name: str, parent_path: str) -> None:
    """
    Delete the configuration file for a specified device.

    Args:
        device_name (str): The name of the device.
        parent_path (str): The path to the parent directory.

    Returns:
        None
    """
    

    # Convert device_name to lowercase and remove any whitespace to ensure consistency
    device_name = device_name.strip().casefold()

    # Open the configuration file for reading
    with open(parent_path + "result.conf", 'r') as f:
        # Read all lines of the file and store them in the config list
        config = f.readlines()

    # Loop through each line in the config list
    for line in config:
        # Check if the line starts with "host"
        if line.startswith('host'):
            # Check if the device_name is in the line (ignoring case and whitespace)
            if device_name in line.strip().casefold().split():
                # If the device_name is found, store the index of the starting line
                start_index = config.index(line)
                # Loop through each line after the starting line
                for i in range(start_index + 1, len(config)):
                    # Check if the line contains a closing brace
                    if '}' in list(config[i]):
                        # If a closing brace is found, store the index of the ending line
                        end_index = i
                        # If both starting and ending indexes are valid,
                        # delete the lines between them from the config list
                        if start_index >= 0 and end_index >= start_index:
                            del config[start_index:end_index + 1]
                            # Open the configuration file for writing and write the modified config list
                            with open(parent_path + "result.conf", 'w') as w:
                                w.writelines(config)
                            # Print a message confirming that the configuration was deleted
                            print(f"'{device_name}' configuration deleted...")
                        else:
                            # If the starting and ending indexes are not valid, print an error message
                            print(f"Configuration file does not contain '{device_name}'...")
                        # Exit the loop once the ending line is found
                        break


def check_for_delete(mac_address: str, device_name: str, ip_address: str, parent_path: str) -> None:
    """
    Given a MAC address, device name, IP address, and parent path, this function checks if the MAC address is in the 
    configuration file. If it is, it gets the string value of the address and the IP address. It then opens the 
    configuration file and loops through each device name. For each device name, it gets the hardware dictionary for
    the current device. If the MAC address is found in the hardware dictionary, it deletes the corresponding device.
    If the IP address is found in the configuration file, it also deletes the corresponding device. If the MAC address
    is not in the configuration file, it deletes the device with the passed device name.

    Args:
        mac_address (str): The MAC address to check.
        device_name (str): The name of the device to delete if the MAC address is not found.
        ip_address (str): The IP address to check.
        parent_path (str): The parent path of the configuration file.

    Returns:
        None
    """
    
    
    # Check if `mac_address` is in the configuration file
    if configure_interface_mac_address(mac_address) is not None:
        # If `mac_address` is found, get the string value of the address and the IP address
        hw_addr = mac_address.strip()
        ip_addr = ip_address.strip()

        # Open the configuration file and parse its contents
        with open(parent_path + "result.conf", "r") as f:
            conf = f.read()
            config = parser.parse(conf)
            dic_config = list(config[0]['host'])

        # Loop through each device name in the configuration file
        for dev_name in dic_config:
            # Get the `hardware` dictionary for the current device
            hardware = config[0]['host'][dev_name].get('hardware', {})

            # If `hw_addr` is found in the `hardware` dictionary, delete the corresponding device
            if hw_addr in hardware.values():
                print(f"Find {hw_addr} for device {dev_name}")
                delete_config_file(dev_name, parent_path)

            # If `ip_addr` is found in the configuration file, delete the corresponding device
            elif ip_addr in config[0]['host'][dev_name].values():
                print(f"Find {ip_addr} for device {dev_name}")
                delete_config_file(dev_name, parent_path)

    # If `mac_address` is not in the configuration file, delete the device with the passed `device_name`
    else:
        delete_config_file(device_name, parent_path)

    
    
def dhcpd_config_file(ip_address: str, interface, event: str = 'None') -> None:
    """
    This function generates a configuration file for the DHCP server based on the provided parameters.
    The function takes in an IP address, an Interface object, and an optional event type string.
    The function first sets a global variable for the parent directory path.
    It then extracts the necessary details from the Interface object and constructs a hostname, MAC address,
    and interface name based on these details.
    Next, the function checks if there is a delete event for the given MAC address, hostname, and IP address.
    If there is no delete event, the function proceeds to configure the interface MAC address.
    Once the MAC address is configured, the function retrieves a DHCP server configuration template, fills in
    the relevant details for the device hostname, host name, MAC address, and IP address, and writes the resulting
    configuration to a file named 'result.conf' in the parent directory.
    If the MAC address is not successfully configured, the function prints a message indicating this.

    Args:
        ip_address (str): The IP address to be assigned to the device
        interface (Interface): An Interface object containing the necessary details for the configuration
        event (str): An optional event type string. Defaults to 'None'.

    Returns:
        None
    """

    global parent_path
    parent_path = parent_path + '/'

    # Extract necessary details from the Interface object
    host_name = interface.device.name
    mac_address = interface.mac_address
    interface_name = interface.name.replace(' ', '_')

    # Construct the hostname for the device
    j2_host = f"{host_name}.{interface_name}"

    # Check if there is a delete event for the given MAC address, hostname, and IP address
    check_for_delete(mac_address, j2_host, ip_address, parent_path)

    # Continue with configuration if there is no delete event
    if event != 'delete':
        # Configure the interface MAC address
        if configure_interface_mac_address(interface.mac_address) is not None:
            # Retrieve the DHCP server configuration template
            environment = Environment(loader=FileSystemLoader(templates_path))
            template = environment.get_template("dhcpd_static.template")
            # Fill in the relevant details in the template
            content = template.render( 
                device_name = j2_host,
                host_name = host_name,
                mac_address = mac_address,
                ip_address = ip_address
            )
            # Write the resulting configuration to a file
            with open(parent_path + 'result.conf', 'a') as f:
                f.write(f"{content}\n")
            print(f"File {'result.conf'} is saved!")
        else:
            print("MAC address isn’t compared...")


def delete_ip_address(interface, ip_address, address_family: int) -> None:
    """
    Deletes an IP address from a network interface.

    Args:
    - interface: An object representing a network interface.
    - ip_address: A string representing the IP address to be deleted.
    - address_family: An integer representing the address family of the IP address (4 for IPv4, 6 for IPv6).

    Returns:
    - None

    Raises:
    - None

    Deletes the specified IP address from the specified network interface. If the specified address is an IPv4 address,
    it is first formatted using the configure_interface_ipv4_address() function. If the specified address is an IPv6
    address, an error message is printed and the function returns without deleting the address.

    After formatting the IP address (if necessary), the function prints a message indicating that it is removing the
    specified address from the specified interface on the specified device. Finally, the function calls the
    dhcpd_config_file() function with the specified interface, IP address, and event set to 'delete'.
    """
    
    
    # Check if the address family is IPv4
    if address_family == 4:
        # If it is, format the IP address using the configure_interface_ipv4_address() function
        ip_address = configure_interface_ipv4_address(ip_address)
    else:
        # If it's not IPv4, print an error message and return without deleting the address
        print("IPv6 not supported")
        return

    # Print a message indicating that the specified address is being removed from the specified interface on the
    # specified device
    print(f"Removing address {ip_address} from interface '{interface.name}' on device '{interface.device.name}'...")

    # Call the dhcpd_config_file() function with the specified interface, IP address, and event set to 'delete'
    dhcpd_config_file(interface, ip_address, event='delete')


def create_ip_address(interface, ip_address, address_family: int) -> None:
    """
    This function creates an IP address for a given interface.

    Args:
        interface: The interface to assign the IP address to.
        ip_address: The IP address to assign.
        address_family: The address family (4 for IPv4, 6 for IPv6).

    Returns:
        None
    """

    # Check if the address family is IPv4.
    if address_family == 4:
        # If so, configure the interface with an IPv4 address.
        ip_address = configure_interface_ipv4_address(ip_address)
    else:
        # If not, print a message saying IPv6 is not supported and return.
        print("IPv6 not supported.")
        return

    # Print a message indicating the IP address is being assigned to the interface.
    print(f"Assigning address {ip_address} to interface '{interface.name}' on device '{interface.device.name}'...")

    # Call the dhcpd_config_file function, passing in the interface, IP address, and event.
    dhcpd_config_file(interface, ip_address, event='create')


def update_ip_address(interface, snapshot_json: Dict[str, Any], ip_address, address_family: int) -> None:
    """
    Update the IP address of the given interface based on the given snapshot JSON.

    Args:
        interface (object): The interface to update.
        snapshot_json (Dict[str, Any]): A JSON snapshot of the interface before the update.
        ip_address (str): The IP address to assign to the interface.
        address_family (int): The IP address family (4 for IPv4, 6 for IPv6).

    Returns:
        None
    """
    
     
    print("Updating IP address...")

    # If there is a snapshot JSON available, try to get the old interface ID
    if snapshot_json:
        try:
            old_interface_id = snapshot_json["prechange"]["assigned_object_id"]
            # If the old interface ID is not the same as the current interface ID, delete the old IP address
            if old_interface_id != interface.id:
                old_interface_data = netbox_api.dcim.interfaces.get(old_interface_id)
                # If the old interface is not management-only, delete the IP address
                if not old_interface_data.mgmt_only: #type: ignore
                    delete_ip_address(interface, ip_address, address_family)
        except (AttributeError, ValueError) as e:
            # Log an error message if the address was not previously assigned
            logger.error(f"Address not previously assigned: {e}")

    # If the address family is IPv4, configure the interface with an IPv4 address
    if address_family == 4:
        ip_address = configure_interface_ipv4_address(ip_address)
        print("IP address V4...")
    else:
        # Otherwise, assume it's IPv6
        print("IPv6")

    # Update the DHCP configuration file for the interface
    dhcpd_config_file(interface, ip_address, event='update')


def manage_ip() -> Response:
    """
    Manage IP address based on the event type, and update it on NetBox.

    Args:
        None

    Returns:
        Response: A Flask Response object with a status code of 204.
    """

    
    # Get data from the webhook sent by NetBox via Flask
    if request.json:
        # Get the ID of the assigned object from the request JSON.
        assigned_object_id = request.json["data"]["assigned_object_id"]

        # Use the NetBox API to get information about the device interface associated with the assigned object.
        device_interface = netbox_api.dcim.interfaces.get(assigned_object_id)

        # Get the IP address from the request JSON.
        device_ips = request.json["data"]["address"]

        # Get the address family (IPv4 or IPv6) from the request JSON.
        ADDRESS_FAMILY_IPV4 = 4
        ADDRESS_FAMILY_IPV6 = 6
        address_family = request.json["data"]["family"]["value"]
        if address_family == ADDRESS_FAMILY_IPV4:
            # If the device interface is marked as management only, log a message and don't make any changes.
            if device_interface.mgmt_only: # type: ignore
                logger.info("Management interface, no changes will be performed.")
            else:
                # If the event type is "deleted", delete the IP address associated with the device interface.
                if request.json["event"] == "deleted":
                    delete_ip_address(device_interface, device_ips, address_family)
                # If the event type is "created", create a new IP address associated with the device interface.
                elif request.json["event"] == "created":
                    create_ip_address(device_interface, device_ips, address_family)
                # If the event type is "updated", update the IP address associated with the device interface.
                elif request.json["event"] == "updated":
                    update_ip_address(device_interface, request.json.get("snapshots"), device_ips, address_family)
        elif address_family == ADDRESS_FAMILY_IPV6:
            pass
        
    # Return a Flask Response object with a status code of 204 (no content).
    return Response(status=204)