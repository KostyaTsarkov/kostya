from flask import request, Response
from config import netbox_api
from journal import journal_template_fill
from global_var import(global_id,
                        global_dcim)
from common import *
from change_intf import *

# Управление интерфейсом
def mng_int():
    """  
    Проверяем полученые данные на соответствие определенным условиям и передаем их на устройства
    :return: Response(status=204)
    """
    
    network_devices_roles = ['access_switch'] # присваиваем значение из netbox ("произвольные" данные)
    user_devices_roles = ['user_device'] # присваиваем значение из netbox ("произвольные" данные)
    
    # Получаем данные через flask от webhook netbox:
    event = request.json["event"]
    mng_int_id = request.json['data']['id']
    prechange = request.json['snapshots']['prechange']
    postchange = request.json['snapshots']['postchange']
    
    # Запрашиваем данные через netbox_api:
    get_device_interface = netbox_api.dcim.interfaces.get(mng_int_id)
    interface_name = get_device_interface.name
    device_role = get_device_interface.device.device_role.slug
    
    global global_id
    global global_dcim 
    global_dcim = 'dcim.device'
    global_id = get_device_interface.device.id
    
    print("{} {}...".format(event.upper(), interface_name))
    
    if get_device_interface.mgmt_only: # проверяем, является ли интерфейс management интерфейсом       
        # > добавляем запись в журнал
        comment,level = '{} is management interface, no changes will be performed'.format(interface_name),'notification'        
        print(journal_template_fill(comment,level,global_id,global_dcim))
        # <
    
    else:
           
        if compare(prechange,postchange) == None: # проверяем, изменились ли данные
            # > добавляем запись в журнал
            comment,level = 'No data for {} {}'.format(event.lower(),interface_name),'informational'
            print(journal_template_fill(comment,level,global_id,global_dcim))
            # <

        elif request.json['data']['enabled'] == False and prechange['enabled'] == True: # проверяем, соответствует ли изменению ВКЛ->ВЫКЛ
            # > добавляем запись в журнал
            comment,level = 'Interface {} is disabled on the device'.format(interface_name),'notification'              
            print(journal_template_fill(comment,level,global_id,global_dcim))
            # <
            change_config_intf(get_device_interface,event='shutdown') # вызываем функцию выключения порта устройства
            
        elif request.json['data']['enabled'] == False and prechange['enabled'] == False: # проверяем, соответствует ли изменению ВЫКЛ->ВЫКЛ
            print('Interface {} was turned off before'.format(interface_name))              
                        
        else: 
            
            if device_role in network_devices_roles: # проверяем, является ли устройство сетевым устройством
                change_config_intf(get_device_interface,event='update') # вызываем функцию внесения изменений настроек порта устройства
            
            elif device_role in user_devices_roles: # проверяем, является ли устройство конечным (пользователя)
                mng_connected_interfaces(get_device_interface) # вызываем функцию внесения изменений настроек связанных портов
        
    return Response(status=204)