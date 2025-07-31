from fask import Flask
from threading import Thread

app = Flask('SqueakBot')
@app.route('/')
def home():
    return "SqueakBot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()