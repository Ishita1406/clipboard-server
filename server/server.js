const express = require('express');
const multer = require('multer');
const path = require('path');
const { setupWebSocket } = require('./wsHandler');
const { loginRouter } = require('./auth');

const app = express();
app.use(express.json());
app.use('/uploads', express.static(path.join(__dirname, '../uploads')));
app.use(loginRouter);

const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, path.join(__dirname, '../uploads/'))
  },
  filename: function (req, file, cb) {
    cb(null, Date.now() + path.extname(file.originalname))
  }
});

const upload = multer({ storage: storage });

app.post('/upload', upload.single('file'), (req, res) => {
  if (!req.file) {
    return res.status(400).send('No file uploaded.');
  }
  const fileUrl = `${req.protocol}://${req.get('host')}/uploads/${req.file.filename}`;
  res.json({ url: fileUrl });
});

const server = app.listen(3000, () =>
  console.log("Server running on port 3000")
);

setupWebSocket(server);
