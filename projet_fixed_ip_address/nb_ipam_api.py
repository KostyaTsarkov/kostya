
from flask import Flask, request, Response
from nornir import InitNornir
import pynetbox
import ipaddress
from jinja2 import Environment, FileSystemLoader
import json
import macaddress
from pydhcpdparser import parser

# Инициализируем nornir

# Init Nornir
nr = InitNornir(
    inventory={
        "plugin": "NetBoxInventory2",
        "options": {
            "nb_url": "http://10.30.1.101:8000",
            "nb_token": "dc5b766afda60e647a9fcc384c736a9689da8618",
            "group_file": "./inventory/groups.yml",
            "defaults_file": "./inventory/defaults.yml",
        },
    },
)

# Инициализируем pynetbox

# Init pynetbox
nb_url = nr.config.inventory.options['nb_url']
nb_token = nr.config.inventory.options['nb_token']
nb = pynetbox.api(
    nb_url,
    token=nb_token
)

# Создаем функцию проверки None

def convert_none_to_str(value):
    return '' if value is None else str(value)

# Создаем функцию извлечения IPv4

def configure_interface_ipv4_address(netbox_ip_address):
    """
    Извлечение IPv4 адреса, маски, сети, префикса, шлюза.
    :param netbox_ip_address: IPv4 адрес (IP/Prefix)
    :return: ip4_address
    """

    ip4_address = format(ipaddress.IPv4Interface(netbox_ip_address).ip)
    ip4_netmask = format(ipaddress.IPv4Interface(netbox_ip_address).netmask)
    ip4_network = format(ipaddress.IPv4Interface(netbox_ip_address).network)
    ip4_prefix = format(ipaddress.IPv4Network(ip4_network).prefixlen)
    ip4_broadcast = format(ipaddress.IPv4Network(ip4_network).broadcast_address)
    ip4_gateway = format(list(ipaddress.IPv4Network(ip4_network).hosts())[-1])

    return(ip4_address)

# Создаем функцию проверки MAC адреса

def confiugure_interface_mac_address(netbox_mac_address):
    """
    Проверяем MAC адрес
    :param netbox_mac_address: MAC address identifier types OUI
    :return: netbox_mac_address
    """

    netbox_mac_address = convert_none_to_str(netbox_mac_address) # если значение None, то преобразуем его в ""

    try:
        macaddress.MAC(netbox_mac_address) # является ли переменная MAC адресом
    except ValueError as error:
        #print(error)
        netbox_mac_address = None
    print("MAC address is {}...".format(netbox_mac_address))
    
    return(netbox_mac_address)

# Создаем функцию очистки конфигурационного файла

def delete_config_file(device_name):
    """
    Если имя находим, то удалаяем все настройки, связанные с этим именем
    :param device_name
    :return: None
    """
    start,end = -2,-2 # start и end должны быть не пустыми и меньше -1
    name = device_name.strip().casefold() # избавляемся от пробелов и игнорируем регистр
    with open("result.conf", 'r') as f: # открываем файл для чтения
        config = f.readlines() # считывем построчно и получаем список
    for line in config:
        if line.startswith('host'): # если в начале строки попадается 'host'
            if name in (s for s in line.strip().casefold().split()): # перебираем строку поэлементно на совпадение с 'name'
                start = config.index(line) # запоминаем индекс
                for i in range(start+1,len(config)): # продолжаем перебирать строки, начиная с индекса
                    if '}' in (s for s in list(config[i])): # разбиваем строку на отдельные символы и проверяем на совпадение с '}'
                        end = i
                        if start >= 0 and end >=start : # значения для среза обязательно должны быть, и второе (end) должно быть не меньше первого (start)
                            del config[start:end+1] # делаем срез списка (избавляемся от строк)
                            with open("result.conf", 'w') as w:
                                w.writelines(config)
                                w.close()
                            print("'{}' is find and deleted there config...".format(device_name))
                        else: print("Configuration file does not contain '{}'...".format(device_name)) 
                        break

# Создаем функцию проверки конфигурационного файла

def test_for_equal(mac_address, device_name,ip_address):
    """
    Проверяем файл конфигурации на наличие в нем каких-либо настроек, связанных с передаваемыми параметрами
    :param device_name
    :param mac_address
    :param ip_address
    :return: None 
    """
    
    """
    Находим составное имя по MAC адресу или по IP адресу
    """
    if confiugure_interface_mac_address(mac_address) != None: 
        hw_addr = mac_address.strip() # избавляемся от пробелов
        ip_addr = ip_address.strip() # избавляемся от пробелов
        with open("result.conf", "r") as f: # открываем файл на чтение
            conf = f.read() # считываем все одной строкой
            f.close() # закрываем файл
        config = parser.parse(conf) # парсим и получаем словарь
        dic_config = list(config[0]['host']) # из словаря делаем список с вложенным словарем
        for dev_name in dic_config: # перебираем словарь
            
            if hw_addr in (s for s in config[0]['host'][dev_name]['hardware'].values()): # если наш MAC присутствует в словаре
                print("Find {} for device {}".format(hw_addr, dev_name))
                delete_config_file(dev_name) # удаляем из словаря все по ключу
           
            elif ip_addr in (s for s in config[0]['host'][dev_name].values()): # если наш IP присутствует в словаре
                print("Find {} for device {}".format(ip_addr, dev_name))
                delete_config_file(dev_name) # удаляем из словаря все по ключу
    else: 
        delete_config_file(device_name)

# Создаем функцию изменения конфига

def dhcpd_config_file(j2_ip_address,j2_interface,event='None'):
    
    """ 
    Заполнение шаблона значениями
    :param j2_interface: интерфейс 
    :param event: событие
    :param j2_ip_address: ip адрес
    :return: None
    """
    j2_host = j2_interface.device.name+'.'+j2_interface.name.replace(" ","_")
    
    test_for_equal(j2_interface.mac_address, j2_host,j2_ip_address)
    
    if event != 'delete':
        
        if confiugure_interface_mac_address(j2_interface.mac_address) != None:

            templates_path = "./templates/"
            environment = Environment(loader=FileSystemLoader(templates_path))
            template = environment.get_template("dhcpd_static.template")

            content = template.render( # заполняем шаблон
            device_name = j2_host,
            host_name = j2_interface.device.name,
            mac_address = j2_interface.mac_address,
            ip_address = j2_ip_address
            )
            print("Filling in the template...\n{}".format(content))
            with open('result.conf', 'a') as fp: # Сохраняем получившийся конфиг
                fp.write(content + '\n')
                fp.close()
            print("File {} is saved!".format("result.conf"))
    
        else: print("MAC address isn’t compared...")

# Удаляем IP-адрес

def delete_ip_address(netbox_interface,netbox_ip_address,netbox_address_family):
    
    """  
    Удаление ip адреса
    :param netbox_interface: ссылка на объект интерфейса pynetbox
    :param netbox_ip_address: IPv4 адрес (IP/Prefix)
    :param netbox_address_family: Версия IP (4|6)
    :return: None
    """
    
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
    dhcpd_config_file(ip_address,interface,event='delete')

# Новый IP-адрес

def create_ip_address(netbox_interface,netbox_ip_address,netbox_address_family):
    
    """  
    Создание ip адреса
    :param netbox_interface: ссылка на объект интерфейса pynetbox
    :param netbox_ip_address: IPv4 адрес (IP/Prefix)
    :param netbox_address_family: Версия IP (4|6)
    :return: None
    """

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
    dhcpd_config_file(ip_address,interface,event='create')

# Изменяем IP-адрес

def update_ip_address(netbox_interface,snapshot_json,netbox_ip_address,netbox_address_family):
    """  
    Изменение ip адреса
    :param netbox_interface: ссылка на объект интерфейса pynetbox
    :param netbox_ip_address: IPv4 адрес (IP/Prefix)
    :param netbox_address_family: Версия IP (4|6)
    :return: None
    """

    print("Updating IP address...")
    if snapshot_json:
        try:
            old_interface_id = snapshot_json["prechange"]["assigned_object_id"]

            if old_interface_id != netbox_interface.id: # если старое назначение принадлежит другому интерфейсу
                old_interface_data = nb.dcim.interfaces.get(old_interface_id) # измененияем конфигурацию перед настройкой нового устройства
                if not old_interface_data.mgmt_only: # если интерфейс не используется для управления! 
                    delete_ip_address(  netbox_interface,
                                        netbox_ip_address,
                                        netbox_address_family)
        except AttributeError:
            print("Address not previously assigned")
        except ValueError:
            print("Address not previously assigned")

    if netbox_address_family == 4:
        ip_address = configure_interface_ipv4_address(netbox_ip_address)
        interface = netbox_interface
        print("IP address V4...")
    else:
        print("IPv6")
    
    """
    Изменяем запись в конфигурационном файле DHCPd-службы
    """
    dhcpd_config_file(ip_address,interface,event='update')

# Создаем функцию для манипулирования IP адресами

def manage_interface_ip_address():
        
    #get_device = request.json["data"]["assigned_object"]["device"]["name"]
    get_device_interface = nb.dcim.interfaces.get(request.json["data"]["assigned_object_id"])    
    get_device_ips = request.json["data"]["address"]
    get_address_family = request.json["data"]["family"]["value"]

    if get_device_interface.mgmt_only: # проверяем, является ли интерфейс management интерфейсов
        print("\tManagement interface, no changes will be performed...")
    else:
            if request.json["event"] == "deleted": # IP адрес будет удален

                delete_ip_address(  netbox_interface=get_device_interface,
                                    netbox_ip_address=get_device_ips,
                                    netbox_address_family=get_address_family
                                    )

            elif request.json["event"] == "created": # IP адрес будет добавлен

                create_ip_address(netbox_interface=get_device_interface,
                                    netbox_ip_address=get_device_ips,
                                    netbox_address_family=get_address_family)

            elif request.json["event"] == "updated": # IP адрес будет добавлен

                update_ip_address(  netbox_interface=get_device_interface,
                                    snapshot_json=request.json.get("snapshots"),
                                    netbox_ip_address=get_device_ips,
                                    netbox_address_family=get_address_family
                                    )
    
    return Response(status=204)

# Создаем экземпляр Flask

# Create a Flask instance
app = Flask(__name__)
app.add_url_rule("/api/fixed_ip",
                 methods=["POST"],
                 view_func=manage_interface_ip_address)

if __name__ == "__main__":
    # If this script is called from the command line, instruct Flask to enable
    # debugging for the app and listen on every IP address on the specified
    # port.
    #app.debug = True
    app.run(host="0.0.0.0", port=8080)

