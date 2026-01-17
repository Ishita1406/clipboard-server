import time
import json
import websocket
import requests
import pyperclip
import os
from dotenv import load_dotenv

load_dotenv()

WS_BASE = os.getenv("WS_BASE")
HTTP_BASE = os.getenv("HTTP_BASE")
USERNAME = os.getenv("USERNAME", "userLinux")
DEVICE_ID = os.getenv("DEVICE_ID","windowsA")

print("WS_BASE:", WS_BASE)
print("HTTP_BASE:", HTTP_BASE)
print("DEVICE_ID:", DEVICE_ID)


# Clipboard helpers (TEXT)

def get_clipboard_text():
    try:
        return pyperclip.paste()
    except Exception as e:
        print("Clipboard read error:", e)
        return None

def set_clipboard_text(text):
    try:
        pyperclip.copy(text)
        return text
    except Exception as e:
        print("Clipboard write error:", e)
        return None

# Login
resp = requests.post(
    f"{HTTP_BASE}/login",
    json={
        "username": USERNAME,
        "deviceId": DEVICE_ID
    },
    timeout=5
)

resp.raise_for_status()
token = resp.json()["token"]


# WebSocket handling
def connect_ws():
    while True:
        try:
            ws = websocket.WebSocket()
            ws.connect(f"{WS_BASE}/?token={token}")
            print("WebSocket connected")
            return ws
        except Exception as e:
            print("WS connect failed, retrying...", e)
            time.sleep(2)

def reconnect_ws():
    global ws
    ws = connect_ws()

ws = connect_ws()

# -------------------------
# Main loop state
# -------------------------

last_text = ""

def send_clipboard_text(text):
    global last_text
    try:
        payload = {
            "type": "text",
            "content": text,
            "timestamp": time.time(),
            "deviceId": DEVICE_ID
        }

        ws.send(json.dumps(payload))
        print("Sent text:", repr(text))
        last_text = text

    except websocket.WebSocketConnectionClosedException:
        print("WS closed while sending, reconnecting...")
        reconnect_ws()

# Main loop

print("Monitoring Windows clipboard (TEXT ONLY)...")

while True:
    current = get_clipboard_text()

    if current is not None and current != last_text:
        send_clipboard_text(current)

    try:
        ws.settimeout(0.1)
        msg = ws.recv()

        if msg:
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                data = None

            if data and data.get("deviceId") != DEVICE_ID:
                if data.get("type") == "text":
                    new_val = set_clipboard_text(data.get("content", ""))
                    if new_val is not None:
                        last_text = new_val
                        print("Received text:", repr(new_val))

    except websocket.WebSocketTimeoutException:
        pass
    except websocket.WebSocketConnectionClosedException:
        print("WS closed, reconnecting...")
        reconnect_ws()
    except Exception as e:
        print("Unexpected error:", e)

    time.sleep(0.5)
