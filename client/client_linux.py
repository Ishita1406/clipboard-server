import subprocess
import time
import json
import websocket
import requests
from dotenv import load_dotenv
import os
load_dotenv()

WS_BASE = os.getenv("WS_BASE")
HTTP_BASE = os.getenv("HTTP_BASE")
print("Server Base URL:", WS_BASE)
USERNAME = "userLinux"
DEVICE_ID = "linux-A" 

def get_clipboard():
    res = subprocess.getoutput("xclip -selection clipboard -o")
    # print("Getting clipboard..." + res)
    return res

def set_clipboard(text):
    subprocess.run("xclip -selection clipboard", input=text, text=True)

# Login
resp = requests.post(f"{HTTP_BASE}/login", json={"username": USERNAME})
token = resp.json()["token"]

ws = websocket.WebSocket()
ws.connect(f"{WS_BASE}/?token={token}")

last = ""

# print("Monitoring clipboard...")

def send_clipboard(text):
    # print("Sending clipboard:", repr(text))
    ws.send(json.dumps({
        "content": text,
        "timestamp": time.time(),
        "deviceId": DEVICE_ID
    }))

while True:
    current = get_clipboard()
    if current != last:
        send_clipboard(current)
        last = current

    try:
        ws.settimeout(0.1)
        msg = ws.recv()
        data = json.loads(msg)
        if data["deviceId"] != DEVICE_ID:
            set_clipboard(data["content"])
            last = data["content"]
    except:
        pass

    time.sleep(0.5)
