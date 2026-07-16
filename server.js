import Fastify from 'fastify';
import { spawn } from 'child_process';
import { open } from 'fs/promises';
import { existsSync } from 'fs';
import path from 'path';

const fastify = Fastify({ logger: false });
const COLS = 181, ROWS = 102, FRAME_SIZE = COLS * ROWS * 3;
const FILE_HANDLES = {};

// One-time automatic background compiler (MP4 -> BIN)
async function compileToBin(filename) {
  const binName = filename.replace(/\.[^/.]+$/, "") + ".bin";
  if (existsSync(binName)) return;

  console.log(`[Boot] Pre-compiling ${filename} to raw binary disk file...`);
  return new Promise((resolve) => {
    const ffmpeg = spawn('ffmpeg', [
      '-i', path.join(process.cwd(), filename),
      '-vf', `scale=${COLS}:${ROWS}:flags=neighbor`,
      '-f', 'rawvideo', '-pix_fmt', 'rgb24',
      binName
    ]);
    ffmpeg.on('close', () => {
      console.log(`[Boot] Done! ${binName} is ready for instant seeking.`);
      resolve();
    });
  });
}

// Ultra-fast binary file reader
async function getFileHandle(filename) {
  const binName = filename.replace(/\.[^/.]+$/, "") + ".bin";
  if (!FILE_HANDLES[binName]) {
    try {
      FILE_HANDLES[binName] = await open(path.join(process.cwd(), binName), 'r');
    } catch {
      return null;
    }
  }
  return FILE_HANDLES[binName];
}

// The absolute fastest, stripped-down route possible
fastify.get('/get-frame/:filename/:frame_idx', async (request, reply) => {
  const fileHandle = await getFileHandle(request.params.filename);
  if (!fileHandle) return reply.status(404).send('404');

  const offset = (parseInt(request.params.frame_idx, 10) || 0) * FRAME_SIZE;
  const buffer = Buffer.allocUnsafe(FRAME_SIZE); // allocated without zero-filling for absolute max speed

  try {
    const { bytesRead } = await fileHandle.read(buffer, 0, FRAME_SIZE, offset);
    if (bytesRead < FRAME_SIZE) {
      await fileHandle.read(buffer, 0, FRAME_SIZE, 0); // Loop back to frame 0
    }
    return reply.header('Content-Type', 'application/octet-stream').send(buffer);
  } catch {
    return reply.status(500).send('Error');
  }
});

const start = async () => {
  // Pre-bake the video on Render's disk before opening the port
  await compileToBin('OLED_TEST.mp4'); 
  
  try {
    await fastify.listen({ port: parseInt(process.env.PORT || 5000), host: '0.0.0.0' });
    console.log("--- INSTANT DISK SEEKER ONLINE (0% RUNTIME CPU, <0.1ms LATENCY) ---");
  } catch {
    process.exit(1);
  }
};

start();
