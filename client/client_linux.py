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
DEVICE_ID = os.getenv("DEVICE_ID")

def get_clipboard_data():
    try:
        # Check targets
        proc = subprocess.run(["xclip", "-selection", "clipboard", "-t", "TARGETS", "-o"], capture_output=True, text=True)
        targets = proc.stdout

        if "text/uri-list" in targets:
            proc = subprocess.run(["xclip", "-selection", "clipboard", "-t", "text/uri-list", "-o"], capture_output=True, text=True)
            # The output is usually 'file:///path/to/file\r\n'
            file_path = proc.stdout.strip().replace("file://", "")
            if os.path.isfile(file_path):
                with open(file_path, "rb") as f:
                    return "file", f.read()
        
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

    elif type == "file":
        try:
            resp = requests.get(content)
            # Extract filename from URL or use a default
            filename = content.split("/")[-1] 
            save_path = f"/tmp/{filename}"
            
            with open(save_path, "wb") as f:
                f.write(resp.content)
            
            # Tell the system we have a file URI
            uri = f"file://{save_path}"
            subprocess.run(
                ["xclip", "-selection", "clipboard", "-t", "text/uri-list"],
                input=uri,
                text=True,
                check=True
            )
            print(f"File saved to {save_path} and path copied to clipboard")
            return content 
        except Exception as e:
            print("Failed to set file clipboard:", e)

def upload_binary(image_data):
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
        elif type == "image" or type == "file":
            url = upload_binary(content)
            if not url:
                return # Failed to upload
            payload["content"] = url

        ws.send(json.dumps(payload))

        print("Sent clipboard")
        last_type = type
        last_content = content  
    except websocket.WebSocketConnectionClosedException:
        print("Send failed: WebSocket closed, reconnecting...")
        reconnect_ws()

while True:
    ctype, current = get_clipboard_data()
    if ctype != "error" and (ctype != last_type or current != last_content):
        send_clipboard(ctype, current)
        last_type = ctype
        last_content = current

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
                msg_type = data.get("type", "text")
                new_val = set_clipboard(msg_type, data["content"])
    
                if new_val is not None:
                    last_type = msg_type
                    last_content = new_val # This prevents the loop from re-sending

    except websocket.WebSocketTimeoutException:
        pass
    except websocket.WebSocketConnectionClosedException:
        # print("WebSocket closed, reconnecting...")
        reconnect_ws()
    except Exception as e:
        print("Unexpected error:", e)


    time.sleep(0.5)