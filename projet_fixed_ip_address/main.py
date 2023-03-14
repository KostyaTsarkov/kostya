from flask import Flask
from nb_ipam_api import manage_interface_ip_address

# Create a Flask instance
app = Flask(__name__)
app.add_url_rule("/api/fixed_ip",
                 methods=["POST"],
                 view_func=manage_interface_ip_address)

if __name__ == "__main__":

    #app.debug = True
    app.run(host="0.0.0.0", port=8080)