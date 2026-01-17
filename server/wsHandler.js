const WebSocket = require('ws');
const jwt = require('jsonwebtoken');
const dotenv = require('dotenv');

const SECRET = process.env.SECRET;
const clients = new Map();

function setupWebSocket(server) {
  const wss = new WebSocket.Server({ server });

  wss.on('connection', (ws, req) => {
    const params = new URLSearchParams(req.url.replace('/?', ''));
    const token = params.get('token');

    try {
      const payload = jwt.verify(token, SECRET);
      clients.set(ws, payload.username);
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

    ws.on('close', () => clients.delete(ws));
  });
}

module.exports = { setupWebSocket };
