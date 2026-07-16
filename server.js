import Fastify from 'fastify';
import { spawn } from 'child_process';
import path from 'path';

const fastify = Fastify();
const FRAME_SIZE = 181 * 102 * 3; // 55,386 bytes

fastify.get('/get-frame/:filename/:frame_idx', (req, reply) => {
  const ffmpeg = spawn('ffmpeg', [
    '-ss', ((parseInt(req.params.frame_idx, 10) || 0) / 30).toFixed(3),
    '-i', path.join(process.cwd(), req.params.filename),
    '-vframes', '1', '-vf', 'scale=181:102:flags=neighbor',
    '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1'
  ]);

  const chunks = [];
  ffmpeg.stdout.on('data', (c) => chunks.push(c));
  ffmpeg.on('close', () => {
    reply.header('Content-Type', 'application/octet-stream')
         .send(Buffer.concat(chunks).subarray(0, FRAME_SIZE));
  });
});

fastify.listen({ port: process.env.PORT || 5000, host: '0.0.0.0' });
