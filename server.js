import Fastify from 'fastify';
import { spawn } from 'child_process';
import path from 'path';

const fastify = Fastify({ logger: false });

const COLS = 181;
const ROWS = 102;
const FRAME_SIZE = COLS * ROWS * 3; // 55,386 bytes

// This will stream and hold the raw video data as it decodes in the background
let videoBuffer = Buffer.alloc(0);
let ffmpegProcess = null;

function startBackgroundStream(filename) {
  const videoPath = path.join(process.cwd(), filename);
  
  console.log(`[FFmpeg] Initiating continuous background stream for ${filename}...`);
  
  // Launch FFmpeg ONCE. It streams the raw uncompressed RGB data to stdout.
  ffmpegProcess = spawn('ffmpeg', [
    '-i', videoPath,
    '-vf', `scale=${COLS}:${ROWS}:flags=neighbor`,
    '-f', 'rawvideo',
    '-pix_fmt', 'rgb24',
    'pipe:1'
  ]);

  ffmpegProcess.stdout.on('data', (chunk) => {
    // Append the freshly decoded frame chunks to our buffer
    videoBuffer = Buffer.concat([videoBuffer, chunk]);
    
    // Safety check: To stay under Render's 512MB RAM, we keep the buffer capped
    // at a maximum of 1000 frames (~55MB). If it goes over, we slice off the oldest frames.
    const maxBufferSize = FRAME_SIZE * 1000;
    if (videoBuffer.length > maxBufferSize) {
      videoBuffer = videoBuffer.subarray(videoBuffer.length - maxBufferSize);
    }
  });

  ffmpegProcess.on('close', () => {
    console.log("[FFmpeg] Video stream finished. Restarting loop...");
    // Auto-restart stream when the video reaches the end
    startBackgroundStream(filename);
  });
}

fastify.get('/get-frame/:filename/:frame_idx', async (request, reply) => {
  const { filename, frame_idx } = request.params;
  const idx = parseInt(frame_idx, 10) || 0;

  // Start the background process on the very first request
  if (!ffmpegProcess) {
    startBackgroundStream(filename);
    // Give FFmpeg a brief 200ms head-start to decode the first few frames
    await new Promise((resolve) => setTimeout(resolve, 200));
  }

  const offset = idx * FRAME_SIZE;

  // If the requested frame is ready in our buffer, slice and send it instantly!
  if (videoBuffer.length >= offset + FRAME_SIZE) {
    const frame = videoBuffer.subarray(offset, offset + FRAME_SIZE);
    reply.header('Content-Type', 'application/octet-stream');
    return reply.send(frame);
  }

  // Fallback: If Roblox is requesting faster than FFmpeg is decoding, send the latest decoded frame
  if (videoBuffer.length >= FRAME_SIZE) {
    const latestOffset = Math.floor(videoBuffer.length / FRAME_SIZE) * FRAME_SIZE - FRAME_SIZE;
    const frame = videoBuffer.subarray(latestOffset, latestOffset + FRAME_SIZE);
    reply.header('Content-Type', 'application/octet-stream');
    return reply.send(frame);
  }

  return reply.status(404).send('Not Ready');
});

const start = async () => {
  try {
    const port = process.env.PORT || 5000;
    await fastify.listen({ port: parseInt(port), host: '0.0.0.0' });
    console.log("--- LIVE BACKGROUND PIPELINE STREAMER ONLINE ---");
  } catch (err) {
    process.exit(1);
  }
};

start();
