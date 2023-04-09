import time
from multiping import multi_ping
from journal import journal_template_fill
from common import *
from nornir import InitNornir
from credentials import(netbox_url,
                        netbox_token)
from jinja2 import Environment, FileSystemLoader
from nornir_napalm.plugins.tasks import napalm_get
from nornir_netmiko.tasks import netmiko_send_config
from global_var import(global_id,
                        global_dcim,
                        templates_path,
                        log)


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
        content = template_fill(j2_interface, template_file,event)
    
    elif event != 'delete':    
        template_file = "cisco_ios_access_interface.template"
        content = template_fill(j2_interface, template_file)
    
    else:
        template_file = "cisco_ios_default_interface.template"
        content = template_fill(j2_interface, template_file)

    return content

# Получаем через napalm интерфейсы с устройства
def push_config_interface(netbox_interface,content,event='None'):
    """  
    Проверка на доступность устройства (ping)
    Подключение к устройству по IP адресу, принадлежащему интерфейсу управления
    Проверка соответствия портов между netbox и реальным устройством
    Отправка конфигурации на устройство
    :param netbox_interface: ссылка на объект интерфейса pynetbox
    :return: None
    """
    
    global global_id
    global global_dcim 
    global_dcim = 'dcim.device'
    global_id = netbox_interface.device.id
    templates_roles = ['access_switch'] # получаем из netbox (произвольные данные)
    device_role = netbox_interface.device.device_role.slug
    
    if device_role in templates_roles:
        attempts = 3 # количество попыток подключения
        attempt_timeout = 5 # время ожидания между попытками в секундах
        fail_count = 0 # количество неудачных попыток
        name = netbox_interface.name
        addrs = []
        filter_query = mgmt_address(netbox_interface) # адрес интерфейса управления
        addrs.append(filter_query)
        
        responses, no_responses = multi_ping(addrs, timeout=0.5, retry=2,ignore_lookup_errors=True)
        print("icmp ping...")
        
        if filter_query in list(responses.keys()): # если адрес интерфейса управления доступен (icmp ping)
            print('{} is available...'.format(addrs))
            
            nr = create_nornir_session()
            sw = nr.filter(hostname = filter_query) # производим отбор по конкретному хосту
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
        comment,level = 'Devices must match the list of {}'.format(templates_roles),'notification'                
        print(journal_template_fill(comment,level,global_id,global_dcim))
        # <