import http from 'http';
import { spawn } from 'child_process';
import path from 'path';

const COLS = 181;
const ROWS = 102;
const FRAME_SIZE = COLS * ROWS * 3; // 55,386 bytes per frame
const BULK_SIZE = 15; // Match your Roblox script's MAX_QUEUE_SIZE

http.createServer((req, res) => {
  const [pathname, queryString] = req.url.split('?');

  if (pathname !== '/get-frame' || !queryString) {
    res.writeHead(404).end();
    return;
  }

  const params = new URLSearchParams(queryString);
  const filename = params.get('file');
  const startFrame = parseInt(params.get('frame'), 10) || 0;

  if (!filename) {
    res.writeHead(400).end('Missing file');
    return;
  }

  const videoPath = path.join(process.cwd(), filename);
  const targetTime = (startFrame / 30).toFixed(4);

  // Instruct FFmpeg to extract 15 sequential frames starting from the requested index
  const ffmpeg = spawn('ffmpeg', [
    '-ss', targetTime,
    '-i', videoPath,
    '-vframes', String(BULK_SIZE),
    '-vf', `scale=${COLS}:${ROWS}:flags=neighbor`,
    '-f', 'rawvideo',
    '-pix_fmt', 'rgb24',
    'pipe:1'
  ]);

  const chunks = [];
  ffmpeg.stdout.on('data', (chunk) => chunks.push(chunk));

  ffmpeg.on('close', () => {
    const bulkBuffer = Buffer.concat(chunks);
    res.writeHead(200, { 
      'Content-Type': 'application/octet-stream',
      'Access-Control-Allow-Origin': '*'
    });
    
    // If we successfully fetched frames, send them. 
    // Otherwise, send blank padding to prevent script stalling.
    if (bulkBuffer.length > 0) {
      res.end(bulkBuffer);
    } else {
      res.end(Buffer.alloc(FRAME_SIZE * BULK_SIZE));
    }
  });

  req.on('close', () => {
    ffmpeg.kill();
  });
}).listen(process.env.PORT || 5000);
