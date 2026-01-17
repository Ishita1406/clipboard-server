# import subprocess
# import time
# import json
# import websocket
# import requests
# from dotenv import load_dotenv
# import os
# import hashlib

# # =======================
# # macOS native clipboard (images)
# # =======================
# from AppKit import NSPasteboard, NSPasteboardTypePNG

# load_dotenv()

# WS_BASE = os.getenv("WS_BASE")
# HTTP_BASE = os.getenv("HTTP_BASE")
# USERNAME = "userMac"
# DEVICE_ID = os.getenv("DEVICE_ID")
# PAIRING_KEY = os.getenv("PAIRING_KEY", "default-key")

# # =======================
# # Clipboard helpers
# # =======================

# def get_clipboard_text():
#     try:
#         data = subprocess.check_output("pbpaste", shell=True)
#         text = data.decode("utf-8")
#         return text.strip()
#     except Exception:
#         return ""

# # =======================
# # read image from macOS clipboard
# # =======================
# def get_clipboard_image():
#     pb = NSPasteboard.generalPasteboard()
#     data = pb.dataForType_(NSPasteboardTypePNG)
#     if data:
#         return bytes(data)
#     return None

# def set_clipboard_text(text):
#     p = subprocess.Popen("pbcopy", stdin=subprocess.PIPE, shell=True)
#     p.communicate(text.encode("utf-8"))

# def fingerprint(data):
#     if isinstance(data, bytes):
#         return hashlib.sha256(data).hexdigest()
#     return hashlib.sha256(data.encode("utf-8")).hexdigest()

# def set_clipboard_image_from_url(url):
#     resp = requests.get(url)
#     resp.raise_for_status()

#     raw_path = "/tmp/clipboard_raw"
#     png_path = "/tmp/clipboard.png"

#     # Save raw image
#     with open(raw_path, "wb") as f:
#         f.write(resp.content)

#     # 🔴 CRITICAL: convert to PNG (macOS-native)
#     subprocess.run(
#         ["sips", "-s", "format", "png", raw_path, "--out", png_path],
#         check=True
#     )

#     # 🔴 Set PNG clipboard
#     subprocess.run(
#         f"""osascript -e 'set the clipboard to (read (POSIX file "{png_path}") as «class PNGf»)'""",
#         shell=True,
#         check=True
#     )


# # =======================
# # unified clipboard reader (image first, then text)
# # =======================
# def get_clipboard_data():
#     img = get_clipboard_image()
#     if img:
#         return "image", img

#     text = get_clipboard_text()
#     if text:
#         return "text", text

#     return None, None

# # =======================
# # upload binary (image)
# # =======================
# def upload_binary(data):
#     files = {
#         "file": ("clipboard.png", data, "image/png")
#     }
#     resp = requests.post(f"{HTTP_BASE}/upload", files=files)
#     resp.raise_for_status()
#     return resp.json()["url"]

# # =======================
# # Login
# # =======================
# resp = requests.post(
#     f"{HTTP_BASE}/login",
#     json={
#         "username": USERNAME,
#         "deviceId": DEVICE_ID,
#         "pairingKey": PAIRING_KEY
#     }
# )

# token = resp.json()["token"]

# # =======================
# # WebSocket helpers
# # =======================
# def connect_ws():
#     while True:
#         try:
#             ws = websocket.WebSocket()
#             ws.connect(f"{WS_BASE}/?token={token}")
#             return ws
#         except Exception:
#             time.sleep(2)

# ws = connect_ws()

# # =======================
# # State
# # =======================
# last_type = None
# last_hash = None

# # =======================
# # Main loop
# # =======================
# while True:
#     ctype, content = get_clipboard_data()

#     if ctype and content:
#         current_hash = fingerprint(content)

#         if ctype != last_type or current_hash != last_hash:
#             payload = {
#                 "type": ctype,
#                 "timestamp": time.time(),
#                 "deviceId": DEVICE_ID,
#                 "originOS": "mac"   #OS awareness
#             }

#             if ctype == "text":
#                 payload["content"] = content

#             elif ctype == "image":
#                 url = upload_binary(content)
#                 payload["content"] = url

#             try:
#                 ws.send(json.dumps(payload))
#                 last_type = ctype
#                 last_hash = current_hash
#                 print(f"Sent {ctype}")
#             except websocket.WebSocketConnectionClosedException:
#                 ws = connect_ws()

#     # =======================
#     # Receive clipboard updates
#     # =======================
#     try:
#         ws.settimeout(0.2)
#         msg = ws.recv()
#         if msg:
#             data = json.loads(msg)

#             if data.get("deviceId") != DEVICE_ID:
#                 if data.get("type") == "text":
#                     set_clipboard_text(data["content"])
#                     last_type = "text"
#                     last_hash = fingerprint(data["content"])
#                     print("Received text")

#                 # macOS image receive can be added later (Linux → mac)
#                 elif data.get("type") == "image":
#                     set_clipboard_image_from_url(data["content"])
#                     last_type = "image"
#                     last_hash = fingerprint(data["content"])
#                     print("Received image")
#     except websocket.WebSocketTimeoutException:
#         pass
#     except websocket.WebSocketConnectionClosedException:
#         ws = connect_ws()
#     except Exception as e:
#         print("Error:", e)


#     time.sleep(1.0)


#NEW CODE
# ================== CHANGED: asyncio added ==================
import asyncio
import subprocess
import json
import websockets
import requests
import os
import sys
from dotenv import load_dotenv

# Ensure we can import from common
sys.path.append(os.path.join(os.path.dirname(__file__), "common"))
from webrtc_peer import WebRTCPeer

print("CLIENT MAC STARTED")

load_dotenv()

WS_BASE = os.getenv("WS_BASE")
HTTP_BASE = os.getenv("HTTP_BASE")
USERNAME = "userMac"
DEVICE_ID = os.getenv("DEVICE_ID")
PAIRING_KEY = os.getenv("PAIRING_KEY")


# ================== Clipboard helpers ==================
def get_clipboard_text():
    try:
        return subprocess.check_output("pbpaste", shell=True).decode()
    except:
        return ""


def set_clipboard_text(text):
    p = subprocess.Popen("pbcopy", stdin=subprocess.PIPE, shell=True)
    p.communicate(text.encode())


# ================== MAIN ASYNC LOGIC ==================
async def main():
    print("Mac async main started")
    
    offline_queue = []

    # ---------- LOGIN ----------
    try:
        resp = requests.post(
            f"{HTTP_BASE}/login",
            json={
                "username": USERNAME,
                "deviceId": DEVICE_ID,
                "pairingKey": PAIRING_KEY
            }
        )
        resp.raise_for_status()
        token = resp.json()["token"]
    except Exception as e:
        print(f"Login failed: {e}")
        return

    print("Mac logged in")

    # ---------- SIGNALING & PEER SETUP ----------
    ws_url = f"{WS_BASE}/?token={token}"
    
    # We need a reference to ws to send signaling messages
    ws_ref = None

    async def signaling_send(data):
        if ws_ref:
            # Add target routing if needed, or just broadcast
            # For now, we broadcast signaling to all peers in room
            await ws_ref.send(json.dumps(data))

    def on_remote_clipboard(content):
        print(f"Received clipboard content: {content[:20]}...")
        set_clipboard_text(content)
        # Update last_text to avoid echo
        nonlocal last_text
        last_text = content

    peer = WebRTCPeer(signaling_send, on_remote_clipboard)
    
    # Hook into channel state for offline queue
    def flush_queue():
        print(f"Flushing {len(offline_queue)} items from offline queue")
        while offline_queue:
            item = offline_queue.pop(0)
            peer.send_clipboard(item)
            
    peer.on_open_callback = flush_queue

    # ---------- CONNECTION LOOP ----------
    async with websockets.connect(ws_url) as ws:
        print("Mac WebSocket connected (Signaling)")
        ws_ref = ws
        
        # Start P2P offer
        await peer.create_offer()

        last_text = ""

        async def listen_ws():
            async for msg in ws:
                data = json.loads(msg)
                # Handle Signaling
                if data.get("senderId") == DEVICE_ID:
                    continue # Ignore own messages if reflected

                if data.get("type") == "offer":
                    await peer.handle_offer(data["sdp"])
                elif data.get("type") == "answer":
                    await peer.handle_answer(data["sdp"])
                elif data.get("type") == "ice":
                    await peer.handle_ice(data["candidate"])

        # Run listener in background
        asyncio.create_task(listen_ws())

        while True:
            # SEND clipboard
            text = get_clipboard_text()
            if text and text != last_text:
                print("Clipboard changed on Mac")
                if peer.is_ready:
                    peer.send_clipboard(text)
                    print("Sent via P2P")
                else:
                    print("P2P not ready, queuing...")
                    if text not in offline_queue:
                        offline_queue.append(text)
                
                last_text = text

            await asyncio.sleep(0.5)


# ================== CHANGED: asyncio entrypoint ==================
if __name__ == "__main__":
    asyncio.run(main())
