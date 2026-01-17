import subprocess
import time
import json
import websocket
import requests
from dotenv import load_dotenv
import os
import hashlib

load_dotenv()

WS_BASE = os.getenv("WS_BASE")
HTTP_BASE = os.getenv("HTTP_BASE")
USERNAME = "userMac"
DEVICE_ID = os.getenv("DEVICE_ID")
PAIRING_KEY = os.getenv("PAIRING_KEY", "default-key")

# ---------- Clipboard Helpers ----------

def get_clipboard_text():
    try:
        data = subprocess.check_output("pbpaste", shell=True)
        text = data.decode("utf-8")
        return text
    except Exception:
        return ""

def set_clipboard_text(text):
    p = subprocess.Popen("pbcopy", stdin=subprocess.PIPE, shell=True)
    p.communicate(text.encode("utf-8"))

def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

# ---------- Auth ----------

resp = requests.post(
    f"{HTTP_BASE}/login",
    json={
        "username": USERNAME,
        "deviceId": DEVICE_ID,
        "pairingKey": PAIRING_KEY
    }
)

token = resp.json()["token"]

# ---------- WebSocket ----------

def connect_ws():
    while True:
        try:
            ws = websocket.WebSocket()
            ws.connect(f"{WS_BASE}/?token={token}")
            return ws
        except Exception:
            time.sleep(2)

ws = connect_ws()

# ---------- State ----------

last_hash = ""

# ---------- Main Loop ----------

while True:
    # Read clipboard
    text = get_clipboard_text()
    text_hash = fingerprint(text)

    if text and text_hash != last_hash:
        payload = {
            "type": "text",
            "content": text,
            "timestamp": time.time(),
            "deviceId": DEVICE_ID,
            "originOS": "mac"
        }

        try:
            ws.send(json.dumps(payload))
            last_hash = text_hash
            print("Sent text")
        except websocket.WebSocketConnectionClosedException:
            ws = connect_ws()

    # Receive clipboard
    try:
        ws.settimeout(0.2)
        msg = ws.recv()
        if msg:
            data = json.loads(msg)

            if data.get("deviceId") != DEVICE_ID and data.get("type") == "text":
                set_clipboard_text(data["content"])
                last_hash = fingerprint(data["content"])
                print("Received text")

    except websocket.WebSocketTimeoutException:
        pass
    except websocket.WebSocketConnectionClosedException:
        ws = connect_ws()
    except Exception as e:
        print("Error:", e)

    time.sleep(1.0)
