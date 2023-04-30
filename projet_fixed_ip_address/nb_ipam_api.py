
from typing import Optional
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
                            print("Configuration file does not contain '{}'...".format(device_name))
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


# Удаляем IP-адрес

def delete_ip_address(netbox_interface,netbox_ip_address,netbox_address_family):
    
    """  
    Удаление ip адреса
    :param netbox_interface: ссылка на объект интерфейса pynetbox
    :param netbox_ip_address: IPv4 адрес (IP/Prefix)
    :param netbox_address_family: Версия IP (4|6)
    :return: None
    """
    ip_address = ''
    interface = ''
    
    print(f"Removing address {netbox_ip_address} "
          f"from interface '{netbox_interface.name}' "
          f"on device '{netbox_interface.device.name}'...")

    if netbox_address_family == 4:
        ip_address = configure_interface_ipv4_address(netbox_ip_address)
        interface = netbox_interface
    else:
        print("IPv6")
    
    """
    Удаляем запись из конфигурационного файла DHCPd-службы
    """
    dhcpd_config_file(interface,ip_address,event='delete')

# Новый IP-адрес

def create_ip_address(netbox_interface,netbox_ip_address,netbox_address_family):
    
    """  
    Создание ip адреса
    :param netbox_interface: ссылка на объект интерфейса pynetbox
    :param netbox_ip_address: IPv4 адрес (IP/Prefix)
    :param netbox_address_family: Версия IP (4|6)
    :return: None
    """
    ip_address = ''
    interface = ''
    
    print(f"Assigning address {netbox_ip_address} "
          f"to interface '{netbox_interface.name}' "
          f"on device '{netbox_interface.device.name}'...")
    
    if netbox_address_family == 4:
        ip_address = configure_interface_ipv4_address(netbox_ip_address)
        interface = netbox_interface
    else:
        print("IPv6")
    
    """
    Добавляем запись в конфигурационный файл DHCPd-службы
    """
    dhcpd_config_file(interface,ip_address,event='create')

# Изменяем IP-адрес

def update_ip_address(netbox_interface,snapshot_json,netbox_ip_address,netbox_address_family):
    """  
    Изменение ip адреса
    :param netbox_interface: ссылка на объект интерфейса pynetbox
    :param netbox_ip_address: IPv4 адрес (IP/Prefix)
    :param netbox_address_family: Версия IP (4|6)
    :return: None
    """
    ip_address = ''
    interface = ''
    
    print("Updating IP address...")
    if snapshot_json:
        try:
            old_interface_id = snapshot_json["prechange"]["assigned_object_id"]

            if old_interface_id != netbox_interface.id: # если старое назначение принадлежит другому интерфейсу
                old_interface_data = netbox_api.dcim.interfaces.get(old_interface_id) # измененияем конфигурацию перед настройкой нового устройства
                if not old_interface_data.mgmt_only: # type: ignore # если интерфейс не используется для управления! 
                    delete_ip_address(  netbox_interface,
                                        netbox_ip_address,
                                        netbox_address_family)
        except (AttributeError, ValueError) as e:
            logger.error("Address not previously assigned: {e}")

    if netbox_address_family == 4:
        ip_address = configure_interface_ipv4_address(netbox_ip_address)
        interface = netbox_interface
        print("IP address V4...")
    else:
        print("IPv6")
    
    """
    Изменяем запись в конфигурационном файле DHCPd-службы
    """
    dhcpd_config_file(interface,ip_address,event='update')

# Создаем функцию для манипулирования IP адресами

def mng_ip() -> Response:

        
    get_device_interface = netbox_api.dcim.interfaces.get(request.json["data"]["assigned_object_id"]) # type: ignore
    get_device_ips = request.json["data"]["address"] # type: ignore
    get_address_family = request.json["data"]["family"]["value"] # type: ignore

    if get_device_interface.mgmt_only: # type: ignore # проверяем, является ли интерфейс management интерфейсов
        #print("\tManagement interface, no changes will be performed...")
        logger.info("Management interface, no changes will be performed.")
    else:
            if request.json["event"] == "deleted": # type: ignore # IP адрес будет удален

                delete_ip_address(  netbox_interface=get_device_interface,
                                    netbox_ip_address=get_device_ips,
                                    netbox_address_family=get_address_family
                                    )

            elif request.json["event"] == "created": # type: ignore # IP адрес будет добавлен

                create_ip_address(netbox_interface=get_device_interface,
                                    netbox_ip_address=get_device_ips,
                                    netbox_address_family=get_address_family)

            elif request.json["event"] == "updated": # type: ignore # IP адрес будет добавлен

                update_ip_address(  netbox_interface=get_device_interface,
                                    snapshot_json=request.json.get("snapshots"), # type: ignore
                                    netbox_ip_address=get_device_ips,
                                    netbox_address_family=get_address_family
                                    )
    
    return Response(status=204)