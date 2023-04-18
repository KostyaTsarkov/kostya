import pathlib

global_id = 0 # ID устройства, нужен для логирования
global_dcim = 'dcim.device' # нужен для логирования (зависит от настроек webhook 'Content types')
#templates_path = "./templates/"
parent_path = str(pathlib.PurePath(__file__).parent)
templates_path = parent_path+"/templates/"
log = ''

# присваиваем значение из netbox ("произвольные" данные)
network_devices_roles = ['access_switch']
# присваиваем значение из netbox ("произвольные" данные)
user_devices_roles = ['user_device']
# произвольный список параметров интерфеса
interface = ['mtu','mac_address','speed','duplex','description','mode','untagged_vlan']