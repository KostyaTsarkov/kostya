from config import netbox_api
from jinja2 import Environment, FileSystemLoader
import json
from global_var import (templates_path)


def journal_template_fill(comment, level, assigned_object_id, dcim):
    """
    Fill in a NetBox journal template with the given arguments.

    Args:
        comment (str): The journal entry comment.
        level (str): The logging level.
        assigned_object_id (int): The assigned object ID.
        dcim (str): The assigned object type.

    Returns:
        str: The journal entry comment with prefix based on logging level.
    """

    if assigned_object_id != 0:
        template_file = "netbox_journals.template"
        environment = Environment(
            loader=FileSystemLoader(templates_path)
        )
        template = environment.get_template(template_file)
        journal = None
        wow = ''
        netbox_level = ''

        kind = ['emergency', 'alert', 'critical', 'error', 'warning',
                'notification', 'informational', 'debugging']
        set_kind = tuple(kind)

        if level in kind: 
            log_level = set_kind.index(level)

            if log_level in range(2):
                netbox_level = 'danger'
                wow = '!!!'
            elif log_level in range(2, 5):
                netbox_level = 'warning'
                wow = '!'
            elif log_level in range(5, 7):
                netbox_level = 'info'
                wow = '.'
        else:
            netbox_level = 'success'
            wow = ''

        try:
            journal = template.render(
                assigned_object_type=dcim,
                assigned_object_id=assigned_object_id,
                created_by='1',
                kind=netbox_level,
                comments=comment + '{}'.format(wow)
            )
        except TypeError:
            print("not all arguments have been transmitted...")
        else:
            if journal is not None:
                journal = json.loads(journal)
                netbox_api.extras.journal_entries.create([journal])
                log = level.upper() + ': ' + comment + wow
                return log
