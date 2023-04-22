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



def parse_interface_name(interface_name):
    """
    Разделяем строку на тип интерфейса и идентификатор интерфейса. 
    :param interface_name: имя интерфейса
    :return: interface_type, interface_id
    """
    interface_pattern = r"^(\D+)(\d+.*)$"
    interface_regex = re.compile(interface_pattern)

    interface_type, interface_id = interface_regex.match(str(interface_name)).groups()  # type: ignore

    return interface_type, interface_id


def configure_interface_ipv4_address(netbox_ip_address='0.0.0.0'):
    """
    Извлекаем IPv4 адреса, маски, сети, префикса, шлюза и возвращем словарь
    :param netbox_ip_address: IPv4 адрес (IP/Prefix)
    :return: ipv4_dic
    """
        
    ipv4_dic = dict()  # type: ignore
    
    global global_dcim
    global global_id
    
    try:
        ip_cidr = ipaddress.ip_interface(netbox_ip_address)
        
        ipv4_dic['ip4_address'] = format(ipaddress.IPv4Interface(ip_cidr).ip)
        ipv4_dic['ip4_netmask'] = format(ipaddress.IPv4Interface(ip_cidr).netmask)
        ipv4_dic['ip4_network'] = format(ipaddress.IPv4Interface(ip_cidr).network)
        ipv4_dic['ip4_prefix'] = format(ipaddress.IPv4Network(ipv4_dic['ip4_network']).prefixlen)
        ipv4_dic['ip4_broadcast'] = format(ipaddress.IPv4Network(ipv4_dic['ip4_network']).broadcast_address)
        
        if (ipaddress.IPv4Network(ipv4_dic['ip4_network']).num_addresses) > 1:
            ipv4_dic['ip4_gateway'] = format(list(ipaddress.IPv4Network(ipv4_dic['ip4_network']).hosts())[-1])
        return(ipv4_dic)
    
    except ValueError:
        # > добавляем запись в журнал
        comment,level = 'address/netmask is invalid for IPv4 {}'.format(netbox_ip_address),'error'                
        log = (journal_template_fill(comment,level,global_id,global_dcim))
        return(log)
        # <
        
        
def mgmt_address(device_interface):
    """
    Извлечение IPv4 адреса интерефейса управления.
    :param device_interface: ссылка на объект интерфейса pynetbox
    :return: mgmt_ip
    """    

    interface_type, interface_id = parse_interface_name(device_interface.name)
    mgmt_ip = configure_interface_ipv4_address(device_interface.device.primary_ip)['ip4_address'] # type: ignore
    
    return(mgmt_ip)


def compare(prechange, postchange):
    """ 
    Сравниваем два объекта и возращаем словарь
    :param prechange: старые данные 
    :param prechange: новые данные
    :return: change
    """   
    compare = DeepDiff(prechange,postchange,exclude_paths="root['last_updated']")
    change = dict()
    change_key = []
    new_value = []

    for key in compare.keys():
        
        if key == 'values_changed' or key == 'type_changes':
            
            for inkey in compare[key].keys():
                change_key.append(re.findall("'([^']*)'", inkey)[0])
                new_value.append(compare[key][inkey]['new_value'])

    change = dict(zip(change_key,new_value)) # объединяем два списка в словарь
    
    if len(change) == 0:
        change = None
    
    return change


def convert_none_to_str(value):
    """ 
    Конвертируем None в пустую строку
    :param value: данные 
    :return: '' or 'value'
    """ 
    return '' if value is None else str(value)


def create_nornir_session():
    """ 
    Инициализируем nornir, но для "hosts" используем данные из netbox
    :return: nr_session
    """
    nr_session = InitNornir(
        inventory={
            "plugin": "NetBoxInventory2",
            "options": {
                "nb_url": netbox_url,
                "nb_token": netbox_token,
                "group_file": "./inventory/groups.yml",
                "defaults_file": "./inventory/defaults.yml",
            },
        },
    )
    return nr_session


# Заполняем шаблон
def cisco_config_interface(j2_interface,event='None'):
    """ 
    Заполнение шаблона значениями, если событие "delete", то заполняем по умолчанию
    :param j2_interface: ссылка на объект интерфейса pynetbox 
    :param event: событие
    :return: content
    """   
    
    
    global global_id
    global global_dcim 
    global_dcim = 'dcim.device'
    global_id = j2_interface.device.id
    
    def template_fill(*args,**kwargs):
    
        environment = Environment(loader=FileSystemLoader(templates_path)) # загружаем шаблон для заполнения
        template = environment.get_template(template_file)
        content = None
        global global_id
        global global_dcim 
        global_dcim = 'dcim.device'
        global_id = j2_interface.device.id
        
        try:
            if event == 'shutdown':
                content = template.render( # заполняем шаблон
                                    interface_name = convert_none_to_str(j2_interface.name)
                                )
            else:
                content = template.render( # заполняем шаблон
                                    interface_name = convert_none_to_str(j2_interface.name),
                                    descr = convert_none_to_str(j2_interface.description),
                                    access_vlan = convert_none_to_str(j2_interface.untagged_vlan.vid),
                                    mode = convert_none_to_str(j2_interface.mode.value)
                                )
                return content
        except: 
            # > добавляем запись в журнал
            comment,level =  'Not enough data to fill out the template','warning'                
            print(journal_template_fill(comment,level,global_id,global_dcim))
            # <
        else:
            #print("Filling in the template...\n{}".format(content)) 
            print("Filling in the template...")

        return content 
        
    if event == 'shutdown':
        template_file = "cisco_ios_shutdown_interface.template"
        content = template_fill(j2_interface, template_file, event)
    
    elif event != 'delete':    
        template_file = "cisco_ios_access_interface.template"
        content = template_fill(j2_interface, template_file)
    
    else:
        template_file = "cisco_ios_default_interface.template"
        content = template_fill(j2_interface, template_file)

    return content


def push_config_interface(netbox_interface,content,event='None'):
    """  
    Проверка на доступность устройства (ping)
    Подключение к устройству по IP адресу, принадлежащему интерфейсу управления
    Проверка соответствия портов между netbox и реальным устройством
    Отправка конфигурации на устройство
    :param netbox_interface: ссылка на объект интерфейса pynetbox
    :return: None
    """
    
    
    #global network_devices_roles
    global global_id
    global global_dcim
    global config_context
    
    global_dcim = 'dcim.device'
    global_id = netbox_interface.device.id
    device_role = netbox_interface.device.device_role.slug
    device_name = netbox_interface.device.name
    network_devices_roles = config_context.network_devices_roles

    if device_role in network_devices_roles:
        attempts = config_context.attempts # количество попыток подключения
        attempt_timeout = config_context.attempt_timeout # время ожидания между попытками в секундах
        fail_count = config_context.fail_count # количество неудачных попыток
        name = netbox_interface.name
        addrs = []
        filter_query = mgmt_address(netbox_interface) # адрес интерфейса управления
        addrs.append(filter_query)
        responses, no_responses = multi_ping(addrs, 
                                             timeout=config_context.timeout, 
                                             retry=config_context.retry,
                                             ignore_lookup_errors=config_context.ignore_lookup_errors)
        print("icmp ping...")
        
        if filter_query in list(responses.keys()): # если адрес интерфейса управления доступен (icmp ping)
            print('{} is available...'.format(addrs))
            
            nr = create_nornir_session()
            sw = nr.filter(hostname = filter_query) # производим отбор по конкретному хосту
            sw.inventory.hosts[device_name].username = config_context.device_username # имя из Netbox
            sw.inventory.hosts[device_name].password = config_context.device_password # пароль из Netbox
            get_int = sw.run(task=napalm_get, getters=['get_interfaces']) # получаем все интерфейсы с устройства в виде словаря
            
            for _ in range(attempts): # попытка подключения к устройству
                print('Attempting to connect {}...'.format(_+1))
        
                if get_int.failed == True: # попытка не удалась
                    fail_count += 1
                    time.sleep(attempt_timeout)
                
                else: # есть подключение
                    print('Connection state is connected...')
            
                    for device in get_int.values():
                        
                        interfaces = device.result['get_interfaces'].keys() # получаем интерфейсы как ключи словаря  
                        if name in (intf for intf in list(interfaces)):
                            print("Find {} for device {}...".format(name, device.host))              
                            result = sw.run(netmiko_send_config,name="Configuration interface.../",config_commands=content)
                            # > добавляем запись в журнал
                            comment,level = 'All operations are performed','success'                
                            print(journal_template_fill(comment,level,global_id,global_dcim))
                            # <
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
        
    devices_keys = ['role','device_id','intf_id'] # список ключей для словаря devices
    devices = []
    devices_names = []
    templates_roles = ['access_switch', 'user_device'] # присваиваем значение из netbox ("произвольные" данные)
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
 
    return Response(status=204)


# Управление интерфейсом
def mng_int():
    """  
    Приходит POST json со статусом updated
    Проверяем полученые данные на соответствие определенным условиям и передаем их на устройства
    :return: Response(status=204)
    """

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

    return Response(status=204)
