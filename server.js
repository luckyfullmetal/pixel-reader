import Fastify from 'fastify';
import { spawn } from 'child_process';
import path from 'path';

const fastify = Fastify({ logger: false });

const COLS = 181;
const ROWS = 102;
const FRAME_SIZE = COLS * ROWS * 3; // 181 * 102 * 3 bytes (RGB)

fastify.get('/get-frame/:filename/:frame_idx', async (request, reply) => {
  const { filename, frame_idx } = request.params;
  const idx = parseInt(frame_idx, 10) || 0;
  
  const videoPath = path.join(process.cwd(), filename);

  const fps = 30; 
  const timestamp = idx / fps;

  return new Promise((resolve) => {
    // CRITICAL SPEED FIX: Put '-ss' BEFORE '-i' so FFmpeg jumps instantly to the frame
    const ffmpeg = spawn('ffmpeg', [
      '-ss', timestamp.toFixed(3), // Seek instantly first
      '-i', videoPath,              // Input file
      '-vframes', '1',
      '-vf', `scale=${COLS}:${ROWS}:flags=neighbor`,
      '-f', 'rawvideo',
      '-pix_fmt', 'rgb24',
      'pipe:1'
    ]);

    const chunks = [];
    ffmpeg.stdout.on('data', (chunk) => {
      chunks.push(chunk);
    });

    ffmpeg.on('close', (code) => {
      if (code === 0 && chunks.length > 0) {
        const frameBuffer = Buffer.concat(chunks);
        
        reply.header('Content-Type', 'application/octet-stream');
        reply.send(frameBuffer.subarray(0, FRAME_SIZE));
      } else {
        reply.status(404).send('404');
      }
      resolve();
    });
  });
});

const start = async () => {
  try {
    const port = process.env.PORT || 5000;
    await fastify.listen({ port: parseInt(port), host: '0.0.0.0' });
    console.log("--- STREAMING DEMON SERVER READY: ULTRA-FAST INPUT SEEKING ---");
  } catch (err) {
    process.exit(1);
  }
};

start();
