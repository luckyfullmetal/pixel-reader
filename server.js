import Fastify from 'fastify';
import { spawn } from 'child_process';
import { readdirSync, existsSync } from 'fs';
import path from 'path';

const fastify = Fastify({ logger: false });

const COLS = 181;
const ROWS = 102;
const FRAME_SIZE = COLS * ROWS * 3; // 181 * 102 * 3 bytes (RGB)

// Global RAM cache for pre-baked 1D frames
const VIDEOS = {};

async function preConvertVideos() {
  console.log("--- STARTING 1D ULTRA-CONVERSION (NODE + FFMPEG) ---");
  const currDir = process.cwd();
  const files = readdirSync(currDir);

  for (const file of files) {
    if (!file.toLowerCase().endsWith('.mp4')) continue;

    const videoPath = path.join(currDir, file);
    
    await new Promise((resolve) => {
      // Direct binary stream from FFmpeg to Node process memory
      const ffmpeg = spawn('ffmpeg', [
        '-i', videoPath,
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
        if (code === 0) {
          const rawBuffer = Buffer.concat(chunks);
          const totalFrames = Math.floor(rawBuffer.length / FRAME_SIZE);
          const frames = [];

          for (let i = 0; i < totalFrames; i++) {
            const start = i * FRAME_SIZE;
            const end = start + FRAME_SIZE;
            frames.push(rawBuffer.subarray(start, end));
          }

          VIDEOS[file] = frames;
          console.log(`[SUCCESS] Cooked '${file}' (${frames.length} frames) into Node 1D RAM arrays.`);
        } else {
          console.log(`[ERROR] Failed to decode ${file}`);
        }
        resolve();
      });
    });
  }
  console.log("--- NODE DEMON SERVER READY: ZERO RUNTIME OVERHEAD ---");
}

// Bare-bones path route designed for maximum speed
fastify.get('/get-frame/:filename/:frame_idx', async (request, reply) => {
  const { filename, frame_idx } = request.params;
  const vList = VIDEOS[filename];

  if (!vList) {
    return reply.status(404).send('404');
  }

  const idx = parseInt(frame_idx, 10) || 0;
  const frameBuffer = vList[idx % vList.length];

  reply.header('Content-Type', 'application/octet-stream');
  return reply.send(frameBuffer);
});

const start = async () => {
  await preConvertVideos();
  try {
    const port = process.env.PORT || 5000;
    await fastify.listen({ port: parseInt(port), host: '0.0.0.0' });
  } catch (err) {
    process.exit(1);
  }
};

start();
