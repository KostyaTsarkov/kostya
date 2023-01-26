from nornir import InitNornir
nr = InitNornir(
    runner={
        "plugin": "threaded",
        "options": {
            "num_workers": 50,
        },
    },
    inventory={
        "plugin": "SimpleInventory",
        "options": {
            "host_file": "./inventory/hosts.yml",
            "group_file": "./inventory/groups.yml",
            "group_file": "./inventory/defaults.yml"
        },
    },
)