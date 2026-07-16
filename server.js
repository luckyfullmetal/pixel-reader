import http from 'http';
import { spawn } from 'child_process';
import path from 'path';

http.createServer((req, res) => {
  // Robust URL splitting
  const segments = req.url.split('/').filter(Boolean);
  
  if (segments.length < 3 || segments[0] !== 'get-frame') {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    return res.end('Endpoint Not Found');
  }

  const filename = segments[1];
  const frameIdx = segments[2];

  // Spawn FFmpeg to output raw RGB24 data
  const ffmpeg = spawn('ffmpeg', [
    '-ss', ((parseInt(frameIdx, 10) || 0) / 30).toFixed(3),
    '-i', path.join(process.cwd(), filename),
    '-vframes', '1',
    '-vf', 'scale=181:102:flags=neighbor',
    '-f', 'rawvideo',
    '-pix_fmt', 'rgb24',
    'pipe:1'
  ]);

  const chunks = [];
  ffmpeg.stdout.on('data', (chunk) => chunks.push(chunk));
  
  ffmpeg.on('close', () => {
    const buffer = Buffer.concat(chunks);
    res.writeHead(200, { 
      'Content-Type': 'application/octet-stream',
      'Access-Control-Allow-Origin': '*'
    });
    res.end(buffer);
  });
}).listen(process.env.PORT || 5000, () => {
  console.log("Bare-metal FFmpeg video pipeline server active on Port 5000");
});
