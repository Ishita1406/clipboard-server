const express = require('express');
const { setupWebSocket } = require('./wsHandler');
const { loginRouter } = require('./auth');

const app = express();
app.use(express.json());
app.use(loginRouter);

const server = app.listen(3000, () =>
  console.log("Server running on port 3000")
);

setupWebSocket(server);
