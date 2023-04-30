from typing import Any, Dict, Optional, Union
from nornir.core import Nornir

import nornir_netmiko
from journal import journal_template_fill
import ipaddress
import re
from deepdiff import DeepDiff
from global_var import *
from flask import request, Response
from config import netbox_api
from types import SimpleNamespace
import time
from multiping import multi_ping
from nornir import InitNornir
from credentials import(netbox_url,
                        netbox_token)
from jinja2 import Environment, FileSystemLoader
from nornir_napalm.plugins.tasks import napalm_get
from nornir_netmiko.tasks import netmiko_send_config



<<<<<<< HEAD
def parse_interface_name(interface_name: str) -> tuple[str, str]:
=======
def parse_interface_name(interface_name: str) -> tuple:
>>>>>>> 39000a4d06de5b6259c886b26c45731bf618c242
    """
    Parses an interface name string into its type and ID components.

    Args:
        interface_name: A string representing the name of the interface to parse.

    Returns:
        A tuple containing two strings: the type of the interface and its ID.

    Raises:
        ValueError: If the interface name is invalid and cannot be parsed.
    """
<<<<<<< HEAD
    interface_pattern = r"^(\D+)(\d+.*)$"
    interface_regex = re.compile(interface_pattern)
    
    try:
        interface_type, interface_id = interface_regex.match(str(interface_name)).groups() # type: ignore
    except AttributeError:
        raise ValueError("Invalid interface name format. The interface name should start with a letter followed by one or more digits and/or letters.") from None
    #interface_type, interface_id = interface_regex.match(str(interface_name)).groups()  # type: ignore
=======

>>>>>>> 39000a4d06de5b6259c886b26c45731bf618c242

    # Define a regular expression pattern to match the interface name
    # The pattern consists of two groups:
    #   1. A non-digit character sequence to capture the interface type
    #   2. A digit sequence followed by any characters to capture the interface ID
    INTERFACE_PATTERN = r"^(\D+)(\d+.*)$"

    # Compile the regular expression pattern into a regex object
    interface_regex = re.compile(INTERFACE_PATTERN)

    try:
        # Attempt to extract the interface type and ID using the regex
        interface_type, interface_id = interface_regex.fullmatch(interface_name).groups()
    except AttributeError:
        # If the regex doesn't match, the interface name is invalid
        raise ValueError("Invalid interface name")

    # Return the interface type and ID as a tuple
    return interface_type, interface_id


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
        journal_template_fill(comment, level, global_id, global_dcim)
        logger.error(comment)

    # Return the dictionary containing the extracted IP address, subnet mask, and broadcast address.
    return ipv4_dict
        
        
def get_management_address(device_interface: Any) -> Union[str, None]:
    """
    This function takes a device interface object and returns the IP address of the device's primary interface,
    which can be used as the management address. If the device_interface object or its attributes are None, None is returned.

    Args:
        device_interface (Any): A device interface object.

    Returns:
        Union[str, None]: The IP address of the device's primary interface, or None if the device_interface object 
        or its attributes are None.
    """
    
    
    # Check if the device_interface object or its name attribute are None, and return None if so
    if not device_interface or not device_interface.name:
        return None

    # Parse the interface name to determine its type and ID
    interface_type, interface_id = parse_interface_name(device_interface.name)

    # Check if the device_interface object or its device attribute or its primary_ip attribute are None,
    # and return None if so
    if not device_interface.device or not device_interface.device.primary_ip:
        return None

    # Get the primary IP address of the device
    primary_ip = device_interface.device.primary_ip

    # Try to configure the interface's IPv4 address using the primary IP address, and return the IP address
    # if successful. If an error occurs (e.g. the primary IP address is invalid), return None
    try:
        return configure_interface_ipv4_address(primary_ip)['ip4_address']
    except (KeyError, TypeError):
        return None


def compare(prechange, postchange):
    """
    Compare two dictionaries and return a dictionary of the differences between them.

    Args:
        prechange (Dict[str, Union[str, int, float]]): The first dictionary to compare.
        postchange (Dict[str, Union[str, int, float]]): The second dictionary to compare.
        exclude_paths (Optional[str], optional): Exclude a specific key from the comparison. Defaults to "root['last_updated']".

    Returns:
        Optional[Dict[str, Union[str, int, float]]]: A dictionary of the differences between the two input dictionaries.
    """
    

    # Compare the two dictionaries using the DeepDiff library
    compare = DeepDiff(prechange, postchange, exclude_paths="root['last_updated']")

    # Initialize an empty dictionary and two empty lists
    change = {}
    change_key = []
    new_value = []

    # Loop through the keys in the 'compare' dictionary
    for key in compare.keys():
        # If the key is 'values_changed' or 'type_changes'
        if key == 'values_changed' or key == 'type_changes':
            # Loop through the keys in the 'values_changed' or 'type_changes' dictionary
            for inkey in compare[key].keys():
                # Extract the key name from the string using regex and append it to the 'change_key' list
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
def convert_none_to_str(data):
    """
    Convert None to an empty string.

    Args:
        data: Any data type.

    Returns:
        A string representing the input data, or an empty string if the input is None.
    """
    return str(data) if data is not None else ''


def create_nornir_session(netbox_url: str, netbox_token: str) -> InitNornir:
    """
    Creates a Nornir object using the NetBoxInventory2 plugin.

    Args:
        netbox_url (str): The URL of the NetBox instance.
        netbox_token (str): The API token to authenticate with NetBox.

    Returns:
        Nornir: The created Nornir object.

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

def cisco_config_interface(interface, event='None'):
    """Fills a Cisco IOS configuration template with data from an interface object.

    Args:
        interface (Interface): An object representing the interface to configure.
        event (str): Optional event type that determines which template to use. Default is 'None'.

    Returns:
        str: The content of the filled template.
    """
    
    
    # Define global variables for the DCIM device and device ID
    global global_id, global_dcim 
    global_dcim = 'dcim.device'
    global_id = interface.device.id

    # This is a nested function that fills a given template with a set of
    # arguments and returns the content. It uses the Jinja2 templating engine.
    def fill_template(*args, **kwargs):
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
                content = template.render(interface_name=convert_none_to_str(interface.name))
            else:
                # Otherwise, pass in the interface name, description, VLAN, and mode
                content = template.render(interface_name=convert_none_to_str(interface.name),
                                           descr=convert_none_to_str(interface.description),
                                           access_vlan=convert_none_to_str(interface.untagged_vlan.vid),
                                           mode=convert_none_to_str(interface.mode.value))
        # If there's not enough data to fill out the template, log a warning and return None
        except:
            comment, level = 'Not enough data to fill out the template', 'warning'
            print(journal_template_fill(comment, level, global_id, global_dcim))
        # Otherwise, log that the template is being filled and return the content
        else:
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
    content = fill_template(interface=interface, template_file=template_file, event=event)
    return content


def push_config_interface(netbox_interface, content: str, event: str = 'None') -> None:
    """
    Pushes configuration to a network interface.

    Parameters:
        netbox_interface (Interface): the Netbox interface object to be configured
        content (str): the configuration content to be pushed
        event (str): not used in the function, just for compatibility with an external system

    Returns:
        None
    """

    #global network_devices_roles
    global global_id, global_dcim, config_context # Define global variables used in the function

    global_dcim = 'dcim.device'
    global_id = netbox_interface.device.id # Get the ID of the device associated with the interface
    device_role = netbox_interface.device.device_role.slug # Get the role of the device associated with the interface
    device_name = netbox_interface.device.name # Get the name of the device associated with the interface
    network_devices_roles = config_context.network_devices_roles # Get the list of device roles allowed in the configuration context

    # Check that the device role is allowed in the configuration context
    if device_role in network_devices_roles:
        attempts = config_context.attempts # Get the number of connection attempts allowed
        attempt_timeout = config_context.attempt_timeout # Get the time to wait between connection attempts
        fail_count = config_context.fail_count # Initialize the number of failed connection attempts to 0
        name = netbox_interface.name # Get the name of the interface to configure
        addrs = []
        filter_query = get_management_address(netbox_interface) # Get the management address of the interface
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

            nr = create_nornir_session(netbox_url, netbox_token) # Create a Nornir session
            sw = nr.filter(hostname = filter_query) # Filter the Nornir session to only include the device with the management address
            sw.inventory.hosts[device_name].username = config_context.device_username # Set the device's username to the one in the configuration context
            sw.inventory.hosts[device_name].password = config_context.device_password # Set the device's password to the one in the configuration context

            # Get all interfaces on the device
            get_int = sw.run(task=napalm_get, getters=['get_interfaces']) 

            # Try to connect to the device
            for _ in range(attempts):
                print('Attempting to connect {}...'.format(_+1))

                # If the connection fails
                if get_int.failed == True:
                    fail_count += 1
                    time.sleep(attempt_timeout)

                # If the connection is successful
                else:
                    print('Connection state is connected...')

                    for device in get_int.values():

                        interfaces = device.result['get_interfaces'].keys() # Get the interfaces as keys in a dictionary  
                        if name in (intf for intf in list(interfaces)):
                            print("Find {} for device {}...".format(name, device.host))              
                            result = sw.run(netmiko_send_config,name="Configuration interface.../",config_commands=content)
                            # Add an entry to the journal
                            comment,level = 'All operations are performed','success'                
                            print(journal_template_fill(comment,level,global_id,global_dcim))

                    break
            if fail_count>=attempts:
                # > добавляем запись в журнал
                comment,level = 'Connection state is failed','error'                
                log = (journal_template_fill(comment,level,global_id,global_dcim))
                # <
            sw.close_connections()
            print("Connection state is closed.")
        
        elif filter_query in no_responses:
            # > добавляем запись в журнал
            comment,level = '{} is not available'.format(addrs),'warning'                
            print(journal_template_fill(comment,level,global_id,global_dcim))
            # <
    else:
        # > добавляем запись в журнал
        comment,level = 'Devices must match the list of {}'.format(network_devices_roles),'notification'                
        print(journal_template_fill(comment,level,global_id,global_dcim))
        # <


# Создаем конфигурацию интерфейса и отправляем её на устройство
def change_config_intf(netbox_interface,event):
    """ 
    Удаляется соединение (cable) в Netbox, настройки порта коммутатора оставляем неизменными 
    :param netbox_interface: ссылка на объект интерфейса pynetbox
    :param event: shutdown|delete|update|create
    :return: None
    """
    
    interface_name = netbox_interface.name

    global global_dcim
    global global_id
    
    try:
        content = cisco_config_interface(netbox_interface,event).split('\n') # type: ignore
        print("{} interface {} config...".format(event.capitalize(),netbox_interface))
        push_config_interface(netbox_interface,content,event)
    except:
            # > добавляем запись в журнал
            comment,level = 'No data for {} {}'.format(event.lower(),interface_name),'informational'
            print(journal_template_fill(comment,level,global_id,global_dcim))
            # <


# Управляем изменениями связанных интерфейсов
def mng_connected_interfaces(device_intf,event,role):
    """  
    Получаем конфигурацию интерфейса устройства пользователя и передаем её интерфейсу устройства-соседа
    Соединение должно быть point-to-point между интерфейсами (Interface)
    :param user_device_intf: ссылка на объект интерфейса pynetbox
    :return: None
    """
    
    global config_context
    global global_dcim
    global global_id
    
    network_devices_roles = config_context.network_devices_roles
    user_devices_roles = config_context.user_devices_roles
    
    def changes_fill(network_device_id,user_device_intf):
 
        changes = dict()
        change_key = ['id'] # добавляем 'ID' устройства-соседа, используемое как ключ
        new_value = [network_device_id]

        for value in user_device_intf: # перебираем список кортежей
            
            if value[0] in config_context.interface and value[1] != '' and value[1] != None: # проверяем, есть ли значение в списке, определенном нами ранее,
                                                                            # значение должно быть заполнено
                change_key.append(value[0])
                
                if isinstance(value[1], dict): # проверяем, является ли значение словарем
                    new_value.append(list(value[1].values())[0]) # превращаем значение словаря в список
                
                else:
                    new_value.append(value[1])
                        
        changes = [dict(zip(change_key,new_value))] # объединяем два списка в словарь       
        
        return changes
    
    
    if role in user_devices_roles and event!='delete':
        
        if device_intf['connected_endpoints_reachable']: # проверяем, есть ли соединение с другим устройством
            #interface = ['mtu','mac_address','speed','duplex','description','mode','untagged_vlan'] # произвольный список параметров интерфеса 
            network_device_id = device_intf['connected_endpoints'][0]['id'] # устройство-сосед (сетевое)    
            changes = changes_fill(network_device_id,device_intf)
            netbox_api.dcim.interfaces.update(changes) # обновляем данные интерфейса через netbox_api
        
        else:
            # > добавляем запись в журнал
            comment,level = 'Neighbor is not reachable for {}'.format(device_intf),'notification'
            print(journal_template_fill(comment,level,global_id,global_dcim))
            # <  
    
    elif role in network_devices_roles and event!='delete':        
        
        if device_intf['connected_endpoints_reachable']: # проверяем, есть ли соединение с другим устройством
            device_intf,network_device_id = netbox_api.dcim.interfaces.get(device_intf['connected_endpoints'][0]['id']),device_intf.id
            #network_device = device_intf.device
            #device_intf = network_device['connected_endpoints'][0]
            changes = changes_fill(network_device_id,device_intf)
            netbox_api.dcim.interfaces.update(changes) # обновляем данные интерфейса через netbox_api
                
        else:
            # > добавляем запись в журнал
            comment,level = 'Neighbor is not reachable for {}'.format(device_intf),'notification'
            print(journal_template_fill(comment,level,global_id,global_dcim))
            # <        
    
    elif role in network_devices_roles and event=='delete':
        changes = dict.fromkeys(config_context.interface, None)
        changes['description'] = ""
        changes['id'] = device_intf.id
        changes['enabled'] = False
        netbox_api.dcim.interfaces.update([changes])
        print('Clear {} netbox interface config'.format(device_intf))
        

# Управление соединением
def mng_cable():
    """  
    Приходит POST json со статусом enabled|created|updated|deleted
    Соединение должно быть point-to-point между интерфейсами (Interface)
    Проверка полученных устройств на соответствие списку (access switch и user device)
    :return: Response(status=204)
    """
    
    try:    
        devices_keys = ['role','device_id','intf_id'] # список ключей для словаря devices
        devices = []
        devices_names = []
        #templates_roles = ['access_switch', 'user_device'] # присваиваем значение из netbox ("произвольные" данные)
        device_roles = []
        regex = "[a|b]_terminations"
        
        # Получаем данные через flask от webhook netbox:
        get_cable = request.json['data'] # type: ignore
        get_event = request.json["event"] # type: ignore
        prechange = request.json['snapshots']['prechange'] # type: ignore
        postchange = request.json['snapshots']['postchange'] # type: ignore
        
        global global_id
        global global_dcim
        global config_context
        global_dcim = 'dcim.cable'
        global_id = get_cable['id']
            
        for key in get_cable.keys(): # заполняем список device_value и объединяем с device_keys в словарь

            if re.match(regex, key) and len(get_cable[key])==1:  # отбираем нужные ключи из словаря по регулярке
                                                                    # при условии, что интерфейс один на устройство
                for _ in range(len(get_cable[key])):
                    device_id = get_cable[key][_]['object']['device']['id'] # ID устройства из json
                    devices_values = []
                    devices_names.append(netbox_api.dcim.devices.get(device_id).name) # type: ignore # наименование устройства через netbox_api
                    devices_values.append(netbox_api.dcim.devices.get(device_id).device_role.slug) # type: ignore # роль устройства через netbox_api
                    devices_values.append(device_id) # id устройства
                    devices_values.append(get_cable[key][_]['object']['id']) # ID интерфейса устройства из json
                    devices.append(dict(zip(devices_keys,devices_values))) # получаем список из словарей
        
        config_context = SimpleNamespace(**dict(netbox_api.dcim.devices.get(device_id).config_context)) # type: ignore
        templates_roles = config_context.network_devices_roles
        templates_roles.extend(config_context.user_devices_roles)
        
        for device in devices: # заполняем список ролей
            device_roles.append(device['role'])
        
        print("{} cable ID #{} between {}...".format(get_event.upper(),get_cable['id'], devices_names))
        
        if set(device_roles).issubset(set(templates_roles)): # проверяем, что получили устройства с разными ролями и соответствущие списку    
            
            for device in devices:
                
                if device['role'] == templates_roles[0]: # нам нужен access switch
                    device_intf_id = device['intf_id'] # получаем ID интерфейса access switchа из нами созданного словаря            
            
            get_device_interface = netbox_api.dcim.interfaces.get(device_intf_id) # type: ignore # по ID находим интерфейс через netbox_api
            interface_name = get_device_interface.name # type: ignore
            interface_mode_802_1Q = convert_none_to_str(get_device_interface.mode.value if get_device_interface.mode else None) # type: ignore
            global_dcim = 'dcim.device'
            global_id = get_device_interface.device.id # type: ignore
            config_context = SimpleNamespace(**dict(netbox_api.dcim.devices.get(global_id).config_context)) # type: ignore
            print("Connection between {} and {}, switch access interface ID: {}...".format(device_roles[0],device_roles[1], device_intf_id)) # type: ignore
            
            if get_device_interface.mgmt_only: # type: ignore # проверяем, является ли интерфейс management интерфейсов
                # > добавляем запись в журнал
                comment,level = '{} is management interface, no changes will be performed'.format(interface_name),'notification'                
                print(journal_template_fill(comment,level,global_id,global_dcim))
                # <
            
            # проверяем, является ли порт транковым (транковый порт не трогаем)
            elif interface_mode_802_1Q in ['tagged','tagged-all']:
                # вызываем функцию внесения изменений настроек порта устройства
                print('Interface {} is mode {}'.format(interface_name,interface_mode_802_1Q))
            
            else:
                
                if get_event == "created": # Конфиг интерфейса будет добавлен
                    mng_connected_interfaces(get_device_interface,event='create',role=templates_roles[0])
                    #change_config_intf(netbox_interface=get_device_interface,event='create')
                
                elif get_event == "deleted": # Конфиг интерфейса будет удален
                    mng_connected_interfaces(get_device_interface,event='delete',role=templates_roles[0])
                    #change_config_intf(netbox_interface=get_device_interface,event='delete')
                
                elif get_device_interface.enabled == False: # type: ignore
                    print('Interface {} was turned off before'.format(interface_name))
                    pass
                
                elif get_event == "updated" and compare(prechange,postchange) != None: # Конфиг интерфейса будет изменен
                    change_config_intf(netbox_interface=get_device_interface,event='update') 
                
                else:
                    # > добавляем запись в журнал
                    comment,level = 'No data for {} {}'.format(get_event.lower(),interface_name),'informational'
                    print(journal_template_fill(comment,level,global_id,global_dcim))
                    # <
                
        else:
            # > добавляем запись в журнал
            comment,level = 'Devices must match the list of {}'.format(templates_roles),'notification'                
            print(comment)
            # <           
    
    except ValueError: 
        print('Something went wrong!')
    
    finally:
        return Response(status=204)


# Управление интерфейсом
def mng_int():
    """  
    Приходит POST json со статусом updated
    Проверяем полученые данные на соответствие определенным условиям и передаем их на устройства
    :return: Response(status=204)
    """
    try:
        # Получаем данные через flask от webhook netbox:
        event = request.json["event"] # type: ignore
        mng_int_id = request.json['data']['id'] # type: ignore
        prechange = request.json['snapshots']['prechange'] # type: ignore
        postchange = request.json['snapshots']['postchange'] # type: ignore

        # Запрашиваем данные через netbox_api:
        get_device_interface = netbox_api.dcim.interfaces.get(mng_int_id)
        interface_name = convert_none_to_str(get_device_interface.name) # type: ignore
        device_role = convert_none_to_str(get_device_interface.device.device_role.slug) # type: ignore
        interface_mode_802_1Q = convert_none_to_str(get_device_interface.mode.value if get_device_interface.mode else None) # type: ignore

        #global network_devices_roles
        #global user_devices_roles
        global global_id
        global global_dcim
        global config_context
        
        global_dcim = 'dcim.device'
        global_id = get_device_interface.device.id # type: ignore
        
        config_context = SimpleNamespace(**dict(netbox_api.dcim.devices.get(global_id).config_context)) # type: ignore
        network_devices_roles = config_context.network_devices_roles
        user_devices_roles = config_context.user_devices_roles
        
        print("{} {}...".format(event.upper(), interface_name))

        # проверяем, является ли интерфейс management интерфейсом
        if get_device_interface.mgmt_only: # type: ignore
            # > добавляем запись в журнал
            comment, level = '{} is management interface, no changes will be performed'.format(
                interface_name), 'notification'
            print(journal_template_fill(comment, level, global_id, global_dcim))
            # <

        # проверяем, изменились ли данные
        elif compare(prechange, postchange) == None:  
            # > добавляем запись в журнал
            comment, level = 'No data for {} {}'.format(
                event.lower(), interface_name), 'informational'
            print(journal_template_fill(comment, level, global_id, global_dcim))
            # <
        
        # проверяем, соответствует ли изменению ВЫКЛ->ВЫКЛ
        elif request.json['data']['enabled'] == False and prechange['enabled'] == False: # type: ignore
            print('Interface {} was turned off before'.format(interface_name))    
            
        # проверяем, является ли устройство сетевым устройством
        elif device_role in network_devices_roles:  
            
            # проверяем, является ли порт транковым (транковый порт не выключаем)
            if interface_mode_802_1Q in ['tagged','tagged-all']:
                # вызываем функцию внесения изменений настроек порта устройства
                print('Interface {} is mode {}'.format(interface_name,interface_mode_802_1Q))
                change_config_intf(get_device_interface, event='update')
            
            else:
                
                # проверяем, соответствует ли изменению ВКЛ->ВЫКЛ
                if request.json['data']['enabled'] == False and prechange['enabled'] == True: # type: ignore
                    # > добавляем запись в журнал
                    comment, level = 'Interface {} is disabled on the device'.format(
                        interface_name), 'notification'
                    print(journal_template_fill(comment, level, global_id, global_dcim))
                    # <
                    # вызываем функцию выключения порта устройства
                    change_config_intf(get_device_interface, event='shutdown')
                
                else: change_config_intf(get_device_interface, event='update')
                
        # проверяем, является ли устройство конечным (пользователя)
        elif device_role in user_devices_roles:
            # вызываем функцию внесения изменений настроек связанных портов
            mng_connected_interfaces(get_device_interface, event='update',role=device_role)
        
        else: print('Device role is "{}"'.format(device_role))

    except ValueError: 
        print('Something went wrong!')
    
    finally:
        return Response(status=204)
