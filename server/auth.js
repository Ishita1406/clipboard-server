const jwt = require('jsonwebtoken');
const express = require('express');
const dotenv = require('dotenv');

dotenv.config();

const SECRET = process.env.SECRET;
const router = express.Router();

router.post('/login', (req, res) => {
  const { username, deviceId, pairingKey } = req.body;
  const payload = {
    username,   // the username of the client
    deviceId,    // the device id of the client
    pairingKey   // the pairing key for grouping devices
  };
  const token = jwt.sign(payload, SECRET, { expiresIn: '1h' });
  res.json({ token });
});

module.exports = {
  loginRouter: router,
  SECRET
};