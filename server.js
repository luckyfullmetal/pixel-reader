import http from 'http';
import { spawn } from 'child_process';
import path from 'path';

http.createServer((req, res) => {
  const [pathname, queryString] = req.url.split('?');

  if (pathname !== '/get-frame' || !queryString) {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    return res.end('Not Found');
  }

  const params = new URLSearchParams(queryString);
  const filename = params.get('file');
  const frameIdx = parseInt(params.get('frame'), 10) || 0;

  if (!filename) {
    res.writeHead(400, { 'Content-Type': 'text/plain' });
    return res.end('Missing file parameter');
  }

  const videoPath = path.join(process.cwd(), filename);
  // Calculate the exact timestamp for the target frame (at 30 FPS)
  const targetTime = (frameIdx / 30).toFixed(4);

  // We place -ss BEFORE the input (-i) for lightning-fast seeking,
  // but use accurate frame-decoding parameters so it doesn't jump to the wrong keyframe.
  const ffmpeg = spawn('ffmpeg', [
    '-ss', targetTime,
    '-i', videoPath,
    '-vframes', '1',
    '-vf', 'scale=181:102:flags=neighbor',
    '-f', 'rawvideo',
    '-pix_fmt', 'rgb24',
    'pipe:1'
  ]);

  res.writeHead(200, { 
    'Content-Type': 'application/octet-stream',
    'Access-Control-Allow-Origin': '*'
  });

  ffmpeg.stdout.pipe(res);

  // Clean up the FFmpeg process if the client aborts the request
  req.on('close', () => {
    ffmpeg.kill();
  });
}).listen(process.env.PORT || 5000, () => {
  console.log("Accurate frame-by-frame seeking server running on Port 5000");
});
