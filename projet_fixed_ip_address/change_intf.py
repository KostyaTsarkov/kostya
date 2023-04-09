from journal import journal_template_fill
from push_config import *
from config import netbox_api
from global_var import(global_id,
                        global_dcim)

# Создаем конфигурацию интерфейса и отправляем её на устройство
def change_config_intf(netbox_interface,event):
    """ 
    Удаляется соединение (cable) в Netbox, настройки порта коммутатора оставляем неизменными 
    :param netbox_interface: ссылка на объект интерфейса pynetbox
    :param event: shutdown|delete|update|create
    :return: None
    """
    
    interface_name = netbox_interface.name
    #event='delete'
    try:
        content = cisco_config_interface(netbox_interface,event).split('\n')
        print("{} interface {} config...".format(event.capitalize(),netbox_interface))
        push_config_interface(netbox_interface,content,event)
    except:
            # > добавляем запись в журнал
            comment,level = 'No data for {} {}'.format(event.lower(),interface_name),'informational'
            print(journal_template_fill(comment,level,global_id,global_dcim))
            # <

# Управляем изменениями связанных интерфейсов
def mng_connected_interfaces(user_device_intf):
    """  
    Получаем конфигурацию интерфейса устройства пользователя и передаем её интерфейсу устройства-соседа
    Соединение должно быть point-to-point между интерфейсами (Interface)
    :param user_device_intf: ссылка на объект интерфейса pynetbox
    :return: None
    """
    
    if user_device_intf['connected_endpoints_reachable']: # проверяем, есть ли соединение с другим устройством
        
        interface = ['mtu','mac_address','speed','duplex','description','mode','untagged_vlan'] # произвольный список параметров интерфеса 
        network_device = user_device_intf['connected_endpoints'][0]['id'] # устройство-сосед (сетевое)
        changes = dict()
        change_key = ['id'] # добавляем 'ID' устройства-соседа, используемое как ключ
        new_value = [network_device]

        for value in user_device_intf: # перебираем список кортежей
            
            if value[0] in interface and value[1] != '' and value[1] != None: # проверяем, есть ли значение в списке, определенном нами ранее,
                                                                              # значение должно быть заполнено
                change_key.append(value[0])
                
                if isinstance(value[1], dict): # проверяем, является ли значение словарем
                    new_value.append(list(value[1].values())[0]) # превращаем значение словаря в список
                
                else:
                    new_value.append(value[1])
        
        changes = [dict(zip(change_key,new_value))] # объединяем два списка в словарь
        netbox_api.dcim.interfaces.update(changes) # обновляем данные интерфейса через netbox_api
    
    else:
        # > добавляем запись в журнал
        comment,level = 'Neighbor is not reachable for {}'.format(user_device_intf),'notification'
        print(journal_template_fill(comment,level,global_id,global_dcim))
        # <        