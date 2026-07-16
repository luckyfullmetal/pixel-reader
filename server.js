import http from 'http';
import { spawn } from 'child_process';
import path from 'path';

http.createServer((req, res) => {
  const [,, filename, frameIdx] = req.url.split('/');
  if (!filename) return res.writeHead(404).end();

  const ffmpeg = spawn('ffmpeg', [
    '-ss', ((parseInt(frameIdx, 10) || 0) / 30).toFixed(3),
    '-i', path.join(process.cwd(), filename),
    '-vframes', '1',
    '-vf', 'scale=181:102:flags=neighbor',
    '-f', 'rawvideo',
    '-pix_fmt', 'rgb24',
    'pipe:1'
  ]);

  res.writeHead(200, { 'Content-Type': 'application/octet-stream' });
  
  // Directly pipe FFmpeg's output stream straight into the HTTP response stream.
  // This bypasses Node's memory entirely for maximum speed.
  ffmpeg.stdout.pipe(res);
}).listen(process.env.PORT || 5000);
