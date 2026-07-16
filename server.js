import Fastify from 'fastify';
import { spawn } from 'child_process';
import path from 'path';

const fastify = Fastify({ logger: false });

const COLS = 181;
const ROWS = 102;
const FRAME_SIZE = COLS * ROWS * 3; // 181 * 102 * 3 bytes (RGB)

// Bare-bones path route designed to extract one exact frame on-the-fly
fastify.get('/get-frame/:filename/:frame_idx', async (request, reply) => {
  const { filename, frame_idx } = request.params;
  const idx = parseInt(frame_idx, 10) || 0;
  
  const videoPath = path.join(process.cwd(), filename);

  // We calculate the timestamp of the exact frame (assuming a standard 30 FPS video)
  // Time = Frame Index / Frame Rate
  const fps = 30; 
  const timestamp = idx / fps;

  return new Promise((resolve) => {
    // We launch FFmpeg to seek (-ss) directly to our exact timestamp,
    // read 1 single frame (-vframes 1), scale it, and pipe the raw bytes to stdout
    const ffmpeg = spawn('ffmpeg', [
      '-ss', timestamp.toString(),
      '-i', videoPath,
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
    console.log("--- STREAMING DEMON SERVER READY: ZERO RAM LEAK ---");
  } catch (err) {
    process.exit(1);
  }
};

start();
