const jwt = require('jsonwebtoken');
const express = require('express');
const dotenv = require('dotenv');

const SECRET = process.env.SECRET;
const router = express.Router();

router.post('/login', (req, res) => {
  const { username } = req.body;
  const token = jwt.sign({ username }, SECRET);
  res.json({ token });
});

module.exports = {
  loginRouter: router,
  SECRET
};
