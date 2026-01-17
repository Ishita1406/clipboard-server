const WebSocket = require('ws');
const jwt = require('jsonwebtoken');
const dotenv = require('dotenv');

dotenv.config();

const SECRET = process.env.SECRET;
const clients = new Map();

function setupWebSocket(server) {
  const wss = new WebSocket.Server({ server });

  wss.on('connection', (ws, req) => {
    const params = new URLSearchParams(req.url.replace('/?', ''));
    const token = params.get('token');


    try {
      const payload = jwt.verify(token, SECRET);
      clients.set(ws, {
        username: payload.username,
        deviceId: payload.deviceId,
        pairingKey: payload.pairingKey
      });
      console.log("Client connected:", payload.username, payload.deviceId);

    } catch {
      ws.close();
      return;
    }

    //    ws.on('message', msg => {
    //     console.log("Received message from", clients.get(ws), ":", msg.toString());
    //     console.log("Currently connected clients:");
    //     for (const [client, user] of clients.entries()) {
    //         console.log(" -", user, client === ws ? "(sender)" : "");
    //     }

    //     for (const [client, user] of clients.entries()) {
    //         if (client !== ws && user === clients.get(ws)) {
    //             console.log("Sending message to client:", user);
    //             client.send(msg.toString());
    //         }
    //     }
    // });

    ws.on('message', msg => {
      const sender = clients.get(ws);
      let data;
      try {
          data = JSON.parse(msg);
      } catch (e) {
          console.error("Invalid JSON:", msg.toString());
          return;
      }

      // Signaling types: 'offer', 'answer', 'ice'
      const signalingTypes = ['offer', 'answer', 'ice'];

      if (signalingTypes.includes(data.type)) {
          console.log(`Relaying ${data.type} from ${sender.deviceId} to peers`);
          
          for (const [client, user] of clients.entries()) {
            // Relay to other devices with same pairingKey
            if (
              client !== ws &&
              user.pairingKey === sender.pairingKey &&
              user.deviceId !== sender.deviceId
            ) {
              // If target is specified, only send to that target
              if (data.target && user.deviceId !== data.target) {
                  continue;
              }
              
              // Attach senderId so receiver knows who sent it
              const forwardedMsg = { ...data, senderId: sender.deviceId };
              client.send(JSON.stringify(forwardedMsg));
            }
          }
      } else {
          console.log("Ignored non-signaling message type:", data.type);
      }
    });


    ws.on('close', () => clients.delete(ws));
  });
}

module.exports = { setupWebSocket };