from flask import request, Response
from config import netbox_api
from change_intf import *
from journal import journal_template_fill
from global_var import(global_id,
                        global_dcim)
from common import *
from change_intf import *

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
    get_cable = request.json['data']
    get_event = request.json["event"]
    prechange = request.json['snapshots']['prechange']
    postchange = request.json['snapshots']['postchange']
    
    global global_id
    global global_dcim 
    global_dcim = 'dcim.cable'
    global_id = get_cable['id']
     
        
    for key in get_cable.keys(): # заполняем список device_value и объединяем с device_keys в словарь

        if re.match(regex, key) and len(get_cable[key])==1:  # отбираем нужные ключи из словаря по регулярке
                                                                # при условии, что интерфейс один на устройство
            for _ in range(len(get_cable[key])):
                device_id = get_cable[key][_]['object']['device']['id'] # ID устройства из json
                devices_values = []
                devices_names.append(netbox_api.dcim.devices.get(device_id).name) # наименование устройства через netbox_api
                devices_values.append(netbox_api.dcim.devices.get(device_id).device_role.slug) # роль устройства через netbox_api
                devices_values.append(device_id) # id устройства
                devices_values.append(get_cable[key][_]['object']['id']) # ID интерфейса устройства из json
                devices.append(dict(zip(devices_keys,devices_values))) # получаем список из словарей
    
    for device in devices: # заполняем список ролей
        device_roles.append(device['role'])
    
    print("{} cable ID #{} between {}...".format(get_event.upper(),get_cable['id'], devices_names))
    
    if set(device_roles) == set(templates_roles): # проверяем, что получили устройства с разными ролями и соответствущие списку    
        
        for device in devices:
            
            if device['role'] == templates_roles[0]: # нам нужен access switch
                device_intf_id = device['intf_id'] # получаем ID интерфейса access switchа из нами созданного словаря            
        
        get_device_interface = netbox_api.dcim.interfaces.get(device_intf_id) # по ID находим интерфейс через netbox_api
        interface_name = get_device_interface.name
        global_dcim = 'dcim.device'
        global_id = get_device_interface.device.id
        print("Connection between {} and {}, switch access interface ID: {}...".format(device_roles[0],device_roles[1], device_intf_id))
        
        if get_device_interface.mgmt_only: # проверяем, является ли интерфейс management интерфейсов
            # > добавляем запись в журнал
            comment,level = '{} is management interface, no changes will be performed'.format(interface_name),'notification'                
            print(journal_template_fill(comment,level,global_id,global_dcim))
            # <
        
        else:
            
            if get_device_interface.enabled == False:
                print('Interface {} was turned off before'.format(interface_name))
                pass
            
            elif get_event == "created": # Конфиг интерфейса будет добавлен
                change_config_intf(netbox_interface=get_device_interface,event='create')

            elif get_event == "updated" and compare(prechange,postchange) != None: # Конфиг интерфейса будет изменен
                change_config_intf(netbox_interface=get_device_interface,event='update') 
            
            elif get_event == "deleted": # Конфиг интерфейса будет удален
                change_config_intf(netbox_interface=get_device_interface,event='delete')
<<<<<<< HEAD
                # вызываем функцию внесения изменений настроек связанных портов
                mng_connected_interfaces(get_device_interface, event='delete')
=======
                mng_connected_interfaces(get_device_interface, event='update')
>>>>>>> 6c0140443661747f03cee7941b76026978f07c9a
            
            else:
                # > добавляем запись в журнал
                comment,level = 'No data for {} {}'.format(get_event.lower(),interface_name),'informational'
                print(journal_template_fill(comment,level,global_id,global_dcim))
                # <
            
    else:
        # > добавляем запись в журнал
        comment,level = 'Devices must match the list of {}'.format(templates_roles),'notification'                
        print(journal_template_fill(comment,level,global_id,global_dcim))
        # <           
 
    return Response(status=204)