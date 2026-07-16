import http from 'http';
import { spawn } from 'child_process';
import path from 'path';

http.createServer((req, res) => {
  // Parse incoming URL path and query parameters manually to keep it bare-metal
  const [pathname, queryString] = req.url.split('?');

  if (pathname !== '/get-frame' || !queryString) {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    return res.end('Not Found');
  }

  // Extract 'file' and 'frame' parameters
  const params = new URLSearchParams(queryString);
  const filename = params.get('file');
  const frameIdx = parseInt(params.get('frame'), 10) || 0;

  if (!filename) {
    res.writeHead(400, { 'Content-Type': 'text/plain' });
    return res.end('Missing file parameter');
  }

  // Spawn FFmpeg to jump directly to the target timestamp and output raw RGB bytes
  const ffmpeg = spawn('ffmpeg', [
    '-ss', (frameIdx / 30).toFixed(3),
    '-i', path.join(process.cwd(), filename),
    '-vframes', '1',
    '-vf', 'scale=181:102:flags=neighbor',
    '-f', 'rawvideo',
    '-pix_fmt', 'rgb24',
    'pipe:1'
  ]);

  // Set the response headers to stream raw octet binary data back to your Roblox buffer
  res.writeHead(200, { 
    'Content-Type': 'application/octet-stream',
    'Access-Control-Allow-Origin': '*'
  });
  
  // Direct stream pipe (Node bypasses local RAM copying entirely)
  ffmpeg.stdout.pipe(res);

  // Safely kill the child process if the request gets terminated early
  req.on('close', () => {
    ffmpeg.kill();
  });
}).listen(process.env.PORT || 5000, () => {
  console.log("Ultra-fast query-param decoder pipeline running on Port 5000");
});
