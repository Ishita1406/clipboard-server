import asyncio
import json
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate

class WebRTCPeer:
    def __init__(self, signaling_send, on_clipboard):
        self.pc = RTCPeerConnection()
        self.signaling_send = signaling_send
        self.on_clipboard = on_clipboard

        self.channel = self.pc.createDataChannel("clipboard")
        self.channel.on("message", self.on_message)

        @self.pc.on("icecandidate")
        async def on_icecandidate(event):
            if event.candidate:
                self.signaling_send({
                    "type": "ice",
                    "candidate": event.candidate.toJSON()
                })

    def on_message(self, message):
        data = json.loads(message)
        if data["type"] == "clipboard":
            self.on_clipboard(data["content"])

    async def create_offer(self):
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)
        self.signaling_send({
            "type": "offer",
            "sdp": self.pc.localDescription.sdp
        })

    async def handle_offer(self, sdp):
        await self.pc.setRemoteDescription(
            RTCSessionDescription(sdp, "offer")
        )
        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)
        self.signaling_send({
            "type": "answer",
            "sdp": self.pc.localDescription.sdp
        })

    async def handle_answer(self, sdp):
        await self.pc.setRemoteDescription(
            RTCSessionDescription(sdp, "answer")
        )

    async def handle_ice(self, candidate):
        await self.pc.addIceCandidate(
            RTCIceCandidate(**candidate)
        )

    def send_clipboard(self, text):
        if self.channel.readyState == "open":
            self.channel.send(json.dumps({
                "type": "clipboard",
                "content": text
            }))
