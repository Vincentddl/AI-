const https = require('https');
const fs = require('fs');
const url = require('url');

const WEBHOOK = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=7a8610e4-f77f-4505-b1c3-844cfca87499';
const content = fs.readFileSync('C:/Users/Vincent Lu/ai-investment-research/scripts/tmp_wecom_1440.md', 'utf-8');

const payload = JSON.stringify({
  msgtype: 'markdown',
  markdown: { content: content }
});

const parsed = url.parse(WEBHOOK);
const options = {
  hostname: parsed.hostname,
  path: parsed.path,
  method: 'POST',
  headers: {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(payload, 'utf-8')
  }
};

const req = https.request(options, (res) => {
  let data = '';
  res.on('data', (chunk) => data += chunk);
  res.on('end', () => {
    console.log('Status:', res.statusCode);
    console.log('Response:', data);
  });
});
req.on('error', (e) => console.error('Error:', e.message));
req.write(payload);
req.end();
