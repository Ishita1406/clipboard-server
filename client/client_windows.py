import time
import json
import websocket
import requests
import pyperclip
import os
from dotenv import load_dotenv

os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""

load_dotenv()

WS_BASE = os.getenv("WS_BASE")
HTTP_BASE = os.getenv("HTTP_BASE")
USERNAME = "userLinux"
DEVICE_ID = os.getenv("DEVICE_ID", "windowsA")
PAIRING_KEY = os.getenv("PAIRING_KEY", "default-key")

print("WS_BASE:", WS_BASE)
print("HTTP_BASE:", HTTP_BASE)
print("DEVICE_ID:", DEVICE_ID)
print("PAIRING_KEY:", PAIRING_KEY)


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


try:
    resp = requests.post(
        f"{HTTP_BASE}/login",
        json={
            "username": USERNAME,
            "deviceId": DEVICE_ID,
            "pairingKey": PAIRING_KEY
        },
        timeout=5,
        proxies={"http": None, "https": None}
    )
    resp.raise_for_status()
    token = resp.json()["token"]
except Exception as e:
    print(f"Login failed: {e}")
    exit(1)

def connect_ws():
    while True:
        try:
            ws = websocket.WebSocket()
            ws.connect(
                f"{WS_BASE}/?token={token}",
                http_proxy_host=None,
                http_proxy_port=None,
                ping_interval=20,
                ping_timeout=5
            )
            print("WebSocket connected")
            return ws
        except Exception as e:
            print("WS connect failed, retrying...", e)
            time.sleep(2)

def reconnect_ws():
    global ws
    ws = connect_ws()

ws = connect_ws()


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
        last_text = text
        print("Sent text:", repr(text))
    except websocket.WebSocketConnectionClosedException:
        print("WS closed while sending, reconnecting...")
        reconnect_ws()
    except Exception as e:
        print("Error sending text:", e)

print("Monitoring Windows clipboard (TEXT only)...")

while True:
    current_text = get_clipboard_text()
    if current_text and current_text != last_text:
        send_clipboard_text(current_text)
        last_text = current_text

    try:
        ws.settimeout(0.1)
        msg = ws.recv()
        if msg:
            data = json.loads(msg)
            if data and data.get("deviceId") != DEVICE_ID:
                if data.get("type") == "text":
                    new_val = set_clipboard_text(data.get("content", ""))
                    if new_val is not None:
                        last_text = new_val
                        print("Received text:", repr(new_val))

    except websocket.WebSocketTimeoutException:
        pass
    except (websocket.WebSocketConnectionClosedException, ConnectionResetError):
        print("WS closed, reconnecting...")
        reconnect_ws()
    except Exception as e:
        print("Loop error:", e)

    time.sleep(0.5)