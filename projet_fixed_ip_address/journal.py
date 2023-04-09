from config import netbox_api
from jinja2 import Environment, FileSystemLoader
import json
from global_var import(global_id,
                        global_dcim,
                        templates_path)

# Заполняем журнал
def journal_template_fill(comment,level,assigned_object_id=global_id,dcim=global_dcim):
    """ 
    Заполняем шаблон значениями, затем отправляем его в Netbox
    и возвращем событие вместе с уровнем важности
    :param comment: событие 
    :param level: уровень важности
    :param assigned_object_id: ID объекта, журнал которого будем заполнять
    :param dcim: обязательное поле Netbox 
    :return: log
    """  
    
    if assigned_object_id !=0:
        template_file = "netbox_journals.template"
        environment = Environment(loader=FileSystemLoader(templates_path)) # загружаем шаблон для заполнения
        template = environment.get_template(template_file)
        journal = None
        wow = ''
        netbox_level = ''
        
        kind = ['emergency','alert','critical','error','warning','notification','informational','debugging',]
        set_kind = tuple(kind) # преобразуем список в кортеж
        
        if level in kind: 
            log_level = set_kind.index(level)
            
            if log_level in range(2):
                netbox_level = 'danger'
                wow = '!!!'
            
            elif log_level in range(2,5):
                netbox_level = 'warning'
                wow = '!'
            
            elif log_level in range(5,7):
                netbox_level = 'info'
                wow = '.'
        
        else: 
            netbox_level = 'success'
            wow = ''
        
        try:
            journal = template.render( # заполняем шаблон
                                    assigned_object_type = dcim,
                                    assigned_object_id = assigned_object_id,
                                    created_by = '1',
                                    kind = netbox_level,
                                    comments = comment + '{}'.format(wow)
                                    )
        except: print("not all arguments have been transmitted...")
        else: 
        
            if journal != None:
                journal = json.loads(journal)
                netbox_api.extras.journal_entries.create([journal])
                log = level.upper()+': '+comment+wow
                return log
    