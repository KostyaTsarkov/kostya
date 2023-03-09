from flask import Flask, request

#Create a Flask instance
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        print("Data received from Webhook is: ", request.json)
        return "Webhook received!"

app.run(host='0.0.0.0', port=8080)
if __name__ == "__main__": app.run()