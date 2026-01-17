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
      clients.set(ws, { username: payload.username, deviceId: payload.deviceId });
      console.log("Client connected:", payload.username, payload.deviceId);

    } catch {
      ws.close();
      return;
    }

    ws.on('message', msg => {
      for (const [client, user] of clients.entries()) {
        if (client !== ws && user === clients.get(ws)) {
          client.send(msg.toString());
        }
      }
    });

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

    ws.on('close', () => clients.delete(ws));
  });
}

module.exports = { setupWebSocket };
