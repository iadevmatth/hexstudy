const express = require('express');
const app = express();
app.use(express.json());

app.post('/webhook', (req, res) => {
  console.log('JSON recebido:', req.body);
  res.status(200).send('OK');
});

app.listen(3000);
