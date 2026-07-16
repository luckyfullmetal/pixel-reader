import http from 'http';
import { spawn } from 'child_process';
import path from 'path';

const COLS = 181;
const ROWS = 102;
const FRAME_SIZE = COLS * ROWS * 3; // Exactly 55,386 bytes per frame
const MAX_BUFFERED_FRAMES = 150; // Keep ~5 seconds of video in RAM

let videoBuffer = Buffer.alloc(0);
let ffmpegProcess = null;
let currentFile = "";

function startFFmpegStream(filename) {
  if (ffmpegProcess) ffmpegProcess.kill();
  
  videoBuffer = Buffer.alloc(0);
  currentFile = filename;
  
  const videoPath = path.join(process.cwd(), filename);
  
  // Decodes the entire video continuously into RAM at a steady rate
  ffmpegProcess = spawn('ffmpeg', [
    '-re', 
    '-i', videoPath,
    '-vf', `scale=${COLS}:${ROWS}:flags=neighbor`,
    '-f', 'rawvideo',
    '-pix_fmt', 'rgb24',
    'pipe:1'
  ]);

  ffmpegProcess.stdout.on('data', (chunk) => {
    videoBuffer = Buffer.concat([videoBuffer, chunk]);
    // Slide the window forward to prevent running out of Render container RAM
    if (videoBuffer.length > FRAME_SIZE * MAX_BUFFERED_FRAMES) {
      videoBuffer = videoBuffer.subarray(videoBuffer.length - (FRAME_SIZE * MAX_BUFFERED_FRAMES));
    }
  });

  ffmpegProcess.on('close', () => {
    // Loop the video stream automatically when it ends
    if (currentFile === filename) startFFmpegStream(filename);
  });
}

http.createServer((req, res) => {
  const [pathname, queryString] = req.url.split('?');

  if (pathname !== '/get-frame' || !queryString) {
    res.writeHead(404).end();
    return;
  }

  const params = new URLSearchParams(queryString);
  const filename = params.get('file');
  const frameIdx = parseInt(params.get('frame'), 10) || 0;

  if (!filename) {
    res.writeHead(400).end('Missing file');
    return;
  }

  // Start the background process on the first request
  if (currentFile !== filename) {
    startFFmpegStream(filename);
  }

  res.writeHead(200, { 
    'Content-Type': 'application/octet-stream',
    'Access-Control-Allow-Origin': '*'
  });

  // Calculate the position of the requested frame inside our sliding RAM buffer
  const targetOffset = (frameIdx * FRAME_SIZE) % Math.max(FRAME_SIZE, videoBuffer.length);

  if (videoBuffer.length >= targetOffset + FRAME_SIZE) {
    res.end(videoBuffer.subarray(targetOffset, targetOffset + FRAME_SIZE));
  } else if (videoBuffer.length >= FRAME_SIZE) {
    // Fallback to the absolute latest frame if the stream is catching up
    res.end(videoBuffer.subarray(videoBuffer.length - FRAME_SIZE));
  } else {
    // Fallback if buffer is completely empty
    res.end(Buffer.alloc(FRAME_SIZE));
  }

  req.on('close', () => {
    // Keep child process alive for future frame requests
  });
}).listen(process.env.PORT || 5000);
