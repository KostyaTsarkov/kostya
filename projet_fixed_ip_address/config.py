import pynetbox
from nornir import InitNornir
from credentials import(netbox_url,
                        netbox_token,
                        device_username,
                        device_password)

# Инициализируем nornir
def create_nornir_session():

    nr_session = InitNornir(
        inventory={
            "plugin": "NetBoxInventory2",
            "options": {
                "nb_url": netbox_url,
                "nb_token": netbox_token,
                "group_file": "./inventory/groups.yml",
                "defaults_file": "./inventory/defaults.yml",
            },
        },
    )
    return nr_session

# Инициализируем pynetbox
def create_netbox_api():

    nr = create_nornir_session()
    nb_url = nr.config.inventory.options['nb_url']
    nb_token = nr.config.inventory.options['nb_token']
    nb = pynetbox.api(
        nb_url,
        token=nb_token
    )
    return nb

nornir_session = create_nornir_session()
netbox_api = create_netbox_api()
