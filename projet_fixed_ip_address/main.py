from flask import Flask
from nb_ipam_api import manage_ip
from common import mng_cable, mng_int

app = Flask(__name__)

"""
Decorator that routes requests to '/api/fixed_ip' URI to this function
with POST method.

Returns:
    The value returned by calling the 'manage_ip' function.
"""


@app.route("/api/fixed_ip", methods=["POST"])
def fixed_ip():
    return manage_ip()


"""
Decorator that routes requests to '/api/cable_change' URI to this function
with POST method.

Returns:
    The value returned by calling the 'mng_cable' function.
"""


@app.route("/api/cable_change", methods=["POST"])
def cable_change():
    return mng_cable()


"""
Decorator that routes requests to '/api/int_update' URI to this function
with POST method.

Returns:
    The value returned by calling the 'mng_int' function.
"""


@app.route("/api/int_update", methods=["POST"])
def int_update():
    return mng_int()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
