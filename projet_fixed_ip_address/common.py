from journal import journal_template_fill
import ipaddress
import re
from deepdiff import DeepDiff
from global_var import(global_id,
                        global_dcim,
                        templates_path)


def parse_interface_name(interface_name):
    """
    Разделяем строку на тип интерфейса и идентификатор интерфейса. 
    :param interface_name: имя интерфейса
    :return: interface_type, interface_id
    """
    interface_pattern = r"^(\D+)(\d+.*)$"
    interface_regex = re.compile(interface_pattern)

    interface_type, interface_id = interface_regex.match(str(interface_name)).groups()

    return interface_type, interface_id


def configure_interface_ipv4_address(netbox_ip_address='0.0.0.0'):
    """
    Извлекаем IPv4 адреса, маски, сети, префикса, шлюза и возвращем словарь
    :param netbox_ip_address: IPv4 адрес (IP/Prefix)
    :return: ipv4_dic
    """
        
    ipv4_dic = dict()
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
    mgmt_ip = configure_interface_ipv4_address(device_interface.device.primary_ip)['ip4_address']
    
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
    :return: '' 
    """ 
    return '' if value is None else str(value)