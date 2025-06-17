from flask import Flask
from threading import Thread

ping_app = Flask('')

@ping_app.route('/')
def home():
    return "A605PatrolBot is Active!"

def keep_alive():
    Thread(target=lambda: ping_app.run(host='0.0.0.0', port=8081)).start()
