const WebSocket = require('ws');

let counter = 0;
const ws = new WebSocket(`ws://localhost:${process.env.PORT}`);

ws.on('open', function open() {
  console.log('Socket opened');

  setTimeout(() => {
    console.log('Closing');
    ws.close(1008, 'Closing message');
  }, 20000)

  ws.ping('Ini ping');

  for (let i = 0; i < 50; i++) {
    ws.send(`!echo ${Math.random().toString(36).substring(7)}`);
  }
});

ws.on('close', (data, res) => {
  console.log('Close request');
  console.log(`Total request: ${counter}`);
});

ws.on('pong', (data) => {
  console.log(`Received pong: ${data}`);
})

ws.on('error', (err) => {
  console.log(`Error: ${err}`);
})

ws.on('message', function incoming(data) {
  console.log(`Received: ${data}`);
  counter += 1;
});
