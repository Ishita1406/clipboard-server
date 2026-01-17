import subprocess
import time
import json
import websocket
import requests
from dotenv import load_dotenv
import os
import hashlib

# =======================
# macOS native clipboard (images)
# =======================
from AppKit import NSPasteboard, NSPasteboardTypePNG

load_dotenv()

WS_BASE = os.getenv("WS_BASE")
HTTP_BASE = os.getenv("HTTP_BASE")
USERNAME = "userMac"
DEVICE_ID = os.getenv("DEVICE_ID")
PAIRING_KEY = os.getenv("PAIRING_KEY", "default-key")

# =======================
# Clipboard helpers
# =======================

def get_clipboard_text():
    try:
        data = subprocess.check_output("pbpaste", shell=True)
        text = data.decode("utf-8")
        return text.strip()
    except Exception:
        return ""

# =======================
# read image from macOS clipboard
# =======================
def get_clipboard_image():
    pb = NSPasteboard.generalPasteboard()
    data = pb.dataForType_(NSPasteboardTypePNG)
    if data:
        return bytes(data)
    return None

def set_clipboard_text(text):
    p = subprocess.Popen("pbcopy", stdin=subprocess.PIPE, shell=True)
    p.communicate(text.encode("utf-8"))

def fingerprint(data):
    if isinstance(data, bytes):
        return hashlib.sha256(data).hexdigest()
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

# =======================
# unified clipboard reader (image first, then text)
# =======================
def get_clipboard_data():
    img = get_clipboard_image()
    if img:
        return "image", img

    text = get_clipboard_text()
    if text:
        return "text", text

    return None, None

# =======================
# upload binary (image)
# =======================
def upload_binary(data):
    files = {
        "file": ("clipboard.png", data, "image/png")
    }
    resp = requests.post(f"{HTTP_BASE}/upload", files=files)
    resp.raise_for_status()
    return resp.json()["url"]

# =======================
# Login
# =======================
resp = requests.post(
    f"{HTTP_BASE}/login",
    json={
        "username": USERNAME,
        "deviceId": DEVICE_ID,
        "pairingKey": PAIRING_KEY
    }
)

token = resp.json()["token"]

# =======================
# WebSocket helpers
# =======================
def connect_ws():
    while True:
        try:
            ws = websocket.WebSocket()
            ws.connect(f"{WS_BASE}/?token={token}")
            return ws
        except Exception:
            time.sleep(2)

ws = connect_ws()

# =======================
# State
# =======================
last_type = None
last_hash = None

# =======================
# Main loop
# =======================
while True:
    ctype, content = get_clipboard_data()

    if ctype and content:
        current_hash = fingerprint(content)

        if ctype != last_type or current_hash != last_hash:
            payload = {
                "type": ctype,
                "timestamp": time.time(),
                "deviceId": DEVICE_ID,
                "originOS": "mac"   #OS awareness
            }

            if ctype == "text":
                payload["content"] = content

            elif ctype == "image":
                url = upload_binary(content)
                payload["content"] = url

            try:
                ws.send(json.dumps(payload))
                last_type = ctype
                last_hash = current_hash
                print(f"Sent {ctype}")
            except websocket.WebSocketConnectionClosedException:
                ws = connect_ws()

    # =======================
    # Receive clipboard updates
    # =======================
    try:
        ws.settimeout(0.2)
        msg = ws.recv()
        if msg:
            data = json.loads(msg)

            if data.get("deviceId") != DEVICE_ID:
                if data.get("type") == "text":
                    set_clipboard_text(data["content"])
                    last_type = "text"
                    last_hash = fingerprint(data["content"])
                    print("Received text")

                # macOS image receive can be added later (Linux → mac)
    except websocket.WebSocketTimeoutException:
        pass
    except websocket.WebSocketConnectionClosedException:
        ws = connect_ws()
    except Exception as e:
        print("Error:", e)


    time.sleep(1.0)
