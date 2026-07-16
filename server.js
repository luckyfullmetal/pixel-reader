import Fastify from 'fastify';
import { spawn } from 'child_process';
import path from 'path';

const fastify = Fastify({ logger: false });

const COLS = 181;
const ROWS = 102;
const FRAME_SIZE = COLS * ROWS * 3; // 181 * 102 * 3 bytes (RGB)

// Configuration for Chunking
const CHUNK_SIZE = 120; // Cache 120 frames (~4 seconds of video) at a time
const VIDEO_CACHES = {}; // Structure: { [filename]: { chunkIndex: Number, frames: [Buffer] } }

// Helper function to decode a specific 4-second chunk into memory
async function loadVideoChunk(filename, chunkIndex) {
  const videoPath = path.join(process.cwd(), filename);
  const startFrame = chunkIndex * CHUNK_SIZE;
  const startTime = startFrame / 30; // 30 FPS target

  return new Promise((resolve) => {
    // Extract exactly CHUNK_SIZE frames starting from startTime
    const ffmpeg = spawn('ffmpeg', [
      '-ss', startTime.toString(),
      '-i', videoPath,
      '-vframes', CHUNK_SIZE.toString(),
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
        const rawBuffer = Buffer.concat(chunks);
        const totalFramesExtracted = Math.floor(rawBuffer.length / FRAME_SIZE);
        const frames = [];

        for (let i = 0; i < totalFramesExtracted; i++) {
          const start = i * FRAME_SIZE;
          const end = start + FRAME_SIZE;
          frames.push(rawBuffer.subarray(start, end));
        }

        resolve(frames);
      } else {
        resolve([]);
      }
    });
  });
}

// Ultra-fast HTTP route
fastify.get('/get-frame/:filename/:frame_idx', async (request, reply) => {
  const { filename, frame_idx } = request.params;
  const idx = parseInt(frame_idx, 10) || 0;

  // Calculate which chunk this frame belongs to
  const targetChunkIndex = Math.floor(idx / CHUNK_SIZE);
  const localFrameIndex = idx % CHUNK_SIZE;

  // Initialize cache for this video if it doesn't exist
  if (!VIDEO_CACHES[filename]) {
    VIDEO_CACHES[filename] = { chunkIndex: -1, frames: [] };
  }

  const cache = VIDEO_CACHES[filename];

  // If the requested frame is not in the currently cached chunk, load it!
  if (cache.chunkIndex !== targetChunkIndex) {
    console.log(`[Cache Miss] Loading chunk ${targetChunkIndex} for ${filename}...`);
    const newFrames = await loadVideoChunk(filename, targetChunkIndex);
    
    if (newFrames.length === 0) {
      return reply.status(404).send('404');
    }

    cache.chunkIndex = targetChunkIndex;
    cache.frames = newFrames;
  }

  // Retrieve the pre-scaled, raw frame from RAM instantly
  const frameBuffer = cache.frames[localFrameIndex];

  if (!frameBuffer) {
    // Wrap around to frame 0 if we exceed video length
    const fallbackFrame = cache.frames[0];
    if (fallbackFrame) {
      reply.header('Content-Type', 'application/octet-stream');
      return reply.send(fallbackFrame);
    }
    return reply.status(404).send('404');
  }

  // Send raw binary to Roblox instantly (< 1ms)
  reply.header('Content-Type', 'application/octet-stream');
  return reply.send(frameBuffer);
});

const start = async () => {
  try {
    const port = process.env.PORT || 5000;
    await fastify.listen({ port: parseInt(port), host: '0.0.0.0' });
    console.log("--- CHUNKED-STREAMING RAM SERVER ONLINE (30+ FPS FIXED) ---");
  } catch (err) {
    process.exit(1);
  }
};

start();
