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

print("CLIENT LINUX STARTED")

load_dotenv()

WS_BASE = os.getenv("WS_BASE")
HTTP_BASE = os.getenv("HTTP_BASE")
USERNAME = "userLinux"
DEVICE_ID = os.getenv("DEVICE_ID")
PAIRING_KEY = os.getenv("PAIRING_KEY")


# ================== Clipboard helpers ==================
def get_clipboard_text():
    try:
        return subprocess.check_output(
            ["xclip", "-selection", "clipboard", "-o"],
            text=True
        )
    except:
        return ""


def set_clipboard_text(text):
    subprocess.run(
        ["xclip", "-selection", "clipboard"],
        input=text,
        text=True
    )


# ================== MAIN ASYNC LOGIC ==================
async def main():
    print("Linux async main started")
    
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

    print("Linux logged in")

    # ---------- SIGNALING & PEER SETUP ----------
    ws_url = f"{WS_BASE}/?token={token}"
    
    # We need a reference to ws to send signaling messages
    ws_ref = None

    async def signaling_send(data):
        if ws_ref:
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
        print("Linux WebSocket connected (Signaling)")
        ws_ref = ws
        
        # Start P2P offer
        await peer.create_offer()

        last_text = ""

        async def listen_ws():
            async for msg in ws:
                data = json.loads(msg)
                # Handle Signaling
                if data.get("senderId") == DEVICE_ID:
                    continue 

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
                print("Clipboard changed on Linux")
                if peer.is_ready:
                    peer.send_clipboard(text)
                    print("Sent via P2P")
                else:
                    print("P2P not ready, queuing...")
                    if text not in offline_queue:
                        offline_queue.append(text)
                
                last_text = text

            await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(main())
