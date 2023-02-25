from nornir_netbox.plugins.inventory.netbox import NetBoxInventory2
from nornir.core.inventory import Inventory, Group

from dotty_dict import dotty

import ruamel.yaml


class CustomNetboxInventory(NetBoxInventory2):

    def __init__(self, config_file, **kwargs):
        with open(config_file, 'r') as f:
            config = ruamel.yaml.safe_load(f)
        super().__init__(
            nb_url=config['nb_url'],
            nb_token=config.get('nb_token'),
            filter_parameters=config['filter_by']
        )
        self.group_by = config['group_by']

    def load(self) -> Inventory:
        ''' Override the base load method so we can add group data
            to our hosts
        '''
        inventory: Inventory = super().load()
        for host in inventory.hosts.values():
            for item in self.group_by:
                dot = dotty(host.data)
                try:
                    group_name = dot.get(item)
                except Exception:
                    group_name = None
                if group_name:
                    host.groups.append(Group(name=group_name))
                    inventory.groups.setdefault(group_name, {})
        return inventory
