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
    print("Getting clipboard..." + res)
    return res

def set_clipboard(text):
    subprocess.run("xclip -selection clipboard", input=text, text=True)

# Login
resp = requests.post(
    f"{HTTP_BASE}/login",
    json={
        "username": USERNAME,
        "deviceId": DEVICE_ID
    }
)
token = resp.json()["token"]


def connect_ws():
    while True:
        try:
            ws = websocket.WebSocket()
            ws.connect(f"{WS_BASE}/?token={token}")
            # print("WebSocket connected")
            return ws
        except Exception as e:
            print("Failed to connect, retrying...", e)
            time.sleep(2)

def reconnect_ws():
    global ws
    # print("Reconnecting WebSocket...")
    ws = connect_ws()


ws = connect_ws()

last = ""

# print("Monitoring clipboard...")

def send_clipboard(text):
    global last
    try:
        print("Sending clipboard:", repr(text))

        ws.send(json.dumps({
            "content": text,
            "timestamp": time.time(),
            "deviceId": DEVICE_ID
        }))

        print("Sent clipboard:", repr(text))
        last = text  # update only if send succeeds
    except websocket.WebSocketConnectionClosedException:
        print("Send failed: WebSocket closed, reconnecting...")
        reconnect_ws()

while True:
    current = get_clipboard()
    if current != last:
        send_clipboard(current)
        last = current

    # try:
    #     ws.settimeout(0.1)
    #     msg = ws.recv()
    #     print("Received message:", msg)
    #     data = json.loads(msg)
    #     if data["deviceId"] != DEVICE_ID:
    #         set_clipboard(data["content"])
    #         last = data["content"]
    # except websocket.WebSocketTimeoutException:
    #     # No new messages, this is fine
    #     pass
    # except websocket.WebSocketConnectionClosedException:
    #     print("WebSocket closed, reconnecting...")
    #     reconnect_ws()
    # except Exception as e:
    #     print("Unexpected error:", e)

    try:
        ws.settimeout(0.1)
        msg = ws.recv()
        if msg:
            try:
                data = json.loads(msg)
                print("Received message:", data)
            except json.JSONDecodeError:
                print("Non-JSON message received:", repr(msg))
                data = None

            if data and data.get("deviceId") != DEVICE_ID:
                set_clipboard(data["content"])
                last = data["content"]
    except websocket.WebSocketTimeoutException:
        pass
    except websocket.WebSocketConnectionClosedException:
        # print("WebSocket closed, reconnecting...")
        reconnect_ws()
    except Exception as e:
        print("Unexpected error:", e)


    time.sleep(0.5)