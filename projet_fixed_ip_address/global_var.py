import pathlib
import logging

#global_id = 0 # ID устройства, нужен для логирования
#global_dcim = 'dcim.device' # нужен для логирования (зависит от настроек webhook 'Content types')
#templates_path = "./templates/"
parent_path = str(pathlib.PurePath(__file__).parent)
templates_path = parent_path+"/templates/"
log = ''

logger = logging.getLogger(__name__)
# присваиваем значение из netbox ("произвольные" данные)
#network_devices_roles = ['access_switch']
# присваиваем значение из netbox ("произвольные" данные)
user_devices_roles = ['user_device']

#mng_connected_interfaces
# произвольный список параметров интерфеса
interface = ['mtu','mac_address','speed','duplex','description','mode','untagged_vlan']

# push_config_interface
attempts = 3 # количество попыток подключения
attempt_timeout = 5 # время ожидания между попытками в секундах
fail_count = 0 # количество неудачных попыток
# ping
timeout = 0.5
retry= 2
ignore_lookup_errors = True

logger = logging.getLogger(__name__)