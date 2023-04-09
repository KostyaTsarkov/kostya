import pathlib

global_id = 0 # ID устройства, нужен для логирования
global_dcim = 'dcim.device' # нужен для логирования (зависит от настроек webhook 'Content types')
#templates_path = "./templates/"
parent_path = str(pathlib.PurePath(__file__).parent)
templates_path = parent_path+"/templates/"
log = ''