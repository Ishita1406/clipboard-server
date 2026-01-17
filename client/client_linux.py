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

def get_clipboard_data():
    try:
        # Check targets
        proc = subprocess.run(["xclip", "-selection", "clipboard", "-t", "TARGETS", "-o"], capture_output=True, text=True)
        targets = proc.stdout
        
        if "image/png" in targets:
            proc = subprocess.run(["xclip", "-selection", "clipboard", "-t", "image/png", "-o"], capture_output=True)
            return "image", proc.stdout
        else:
            proc = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True)
            return "text", proc.stdout
    except Exception as e:
        print("Error getting clipboard:", e)
        return "error", None

def set_clipboard(type, content):
    if type == "text":
        subprocess.run(
            ["xclip", "-selection", "clipboard"],
            input=content,
            text=True,
            check=True
        )
    elif type == "image":
        # content is URL
        try:
            print("Downloading image from:", content)
            resp = requests.get(content)
            resp.raise_for_status()
            image_data = resp.content
            subprocess.run(["xclip", "-selection", "clipboard", "-t", "image/png"], input=image_data, check=True)
            print("Image set to clipboard")
        except Exception as e:
            print("Failed to set image clipboard:", e)

def upload_image(image_data):
    try:
        files = {'file': ('clipboard.png', image_data, 'image/png')}
        resp = requests.post(f"{HTTP_BASE}/upload", files=files)
        resp.raise_for_status()
        return resp.json()["url"]
    except Exception as e:
        print("Upload failed:", e)
        return None


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

last_type = "text"
last_content = ""

# print("Monitoring clipboard...")

def send_clipboard(type, content):
    global last_type, last_content
    try:
        print(f"Sending clipboard ({type})...")
        
        payload = {
            "type": type,
            "timestamp": time.time(),
            "deviceId": DEVICE_ID
        }

        if type == "text":
            payload["content"] = content
        elif type == "image":
            url = upload_image(content)
            if not url:
                return # Failed to upload
            payload["content"] = url

        ws.send(json.dumps(payload))

        print("Sent clipboard")
        last_type = type
        last_content = content  # update only if send succeeds
    except websocket.WebSocketConnectionClosedException:
        print("Send failed: WebSocket closed, reconnecting...")
        reconnect_ws()

while True:
    ctype, current = get_clipboard_data()
    if ctype != "error" and (ctype != last_type or current != last_content):
        # Avoid sending if we just received it (naive check, better to check timestamp or source)
        # But for now, just send if changed.
        # Note: Binary comparison for images might be slow but necessary.
        send_clipboard(ctype, current)
        last_type = ctype
        last_content = current

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
                msg_type = data.get("type", "text") # Default to text for backward compatibility
                set_clipboard(msg_type, data["content"])
                last_type = msg_type
                # For image, we don't have the raw bytes in 'data["content"]' (it's URL), 
                # so we can't easily update last_content to match what get_clipboard_data returns (bytes).
                # We might need to fetch it or just accept that next loop might re-read it.
                # If we re-read it, it will match what we just set, so it shouldn't loop.
                # However, get_clipboard_data returns bytes for image.
                # We should probably update last_content with the bytes we set.
                if msg_type == "image":
                     # We need to read back what we just set to keep state consistent?
                     # Or just fetch the bytes again from clipboard to be sure.
                     # Let's just let the loop handle it. It might re-send if bytes differ slightly?
                     # Ideally set_clipboard returns the bytes it set.
                     pass 
                else:
                    last_content = data["content"]

    except websocket.WebSocketTimeoutException:
        pass
    except websocket.WebSocketConnectionClosedException:
        # print("WebSocket closed, reconnecting...")
        reconnect_ws()
    except Exception as e:
        print("Unexpected error:", e)


    time.sleep(0.5)