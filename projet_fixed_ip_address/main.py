# Create a Flask instance
from flask import Flask
from nb_ipam_api import mng_ip
#from nb_sw_cable_api import mng_cable
#from nb_sw_int_api import mng_int
from common import mng_cable, mng_int

# Create a Flask instance
app = Flask(__name__)
"""
Webhook POST
    Name:'Fixed IP into DHCPd'
    Content types: 'IPAM > IP Address'
"""
app.add_url_rule("/api/fixed_ip",
                 methods=["POST"],
                 view_func=mng_ip)
"""
Webhook POST
    Name:'Change the cable'
    Content types: 'DCIM > Cable'
"""
app.add_url_rule("/api/cable_change",
                 methods=['POST'],
                 view_func=mng_cable)
"""
Webhook POST
    Name:'Update the interface'
    Content types: 'DCIM > Interfaces'
"""
app.add_url_rule("/api/int_update",
                 methods=['POST'],
                 view_func=mng_int)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
