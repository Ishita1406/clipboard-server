import websocket
import json
import threading

class SignalingClient:
    def __init__(self, ws_url, token, on_message):
        self.ws_url = f"{ws_url}/?token={token}"
        self.on_message = on_message

        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=self._on_message
        )

    def _on_message(self, ws, message):
        data = json.loads(message)
        self.on_message(data)

    def send(self, data):
        self.ws.send(json.dumps(data))

    def start(self):
        thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        thread.start()
