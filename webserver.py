from flask import Flask
from threading import Thread
import os

app = Flask('SqueakBot')

@app.route('/')
def home():
    return "SqueakBot is running!"

def run():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()