import http from 'http';
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';

const WIDTH = 181;
const HEIGHT = 102;
const FRAME_SIZE = WIDTH * HEIGHT * 3;
const CHUNK_SIZE = 30; // Number of frames per network batch
const PORT = process.env.PORT || 8080;
const videoCache = {};

function prepareRawData(videoFile) {
    const ext = path.extname(videoFile);
    const baseName = path.basename(videoFile, ext);
    const binFile = `${baseName}.bin`;

    if (fs.existsSync(binFile)) {
        const fullBuffer = fs.readFileSync(binFile);
        const totalFrames = Math.floor(fullBuffer.length / FRAME_SIZE);
        videoCache[videoFile] = { buffer: fullBuffer, totalFrames };
        return;
    }

    const ffmpeg = spawn("ffmpeg", [
        "-i", videoFile,
        "-vf", `scale=${WIDTH}:${HEIGHT}:flags=neighbor`,
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "pipe:1"
    ]);

    let buffers = [];
    ffmpeg.stdout.on('data', (chunk) => { buffers.push(chunk); });
    ffmpeg.on('close', (code) => {
        if (code !== 0) return;
        const fullBuffer = Buffer.concat(buffers);
        const totalFrames = Math.floor(fullBuffer.length / FRAME_SIZE);
        fs.writeFileSync(binFile, fullBuffer);
        videoCache[videoFile] = { buffer: fullBuffer, totalFrames };
    });
}

fs.readdirSync('.').forEach(file => {
    if (file.endsWith('.mp4')) {
        prepareRawData(file);
    }
});

const server = http.createServer((req, res) => {
    const url = new URL(req.url, `http://${req.headers.host}`);
    if (url.pathname !== "/stream") {
        res.writeHead(404);
        return res.end();
    }

    const videoName = url.searchParams.get("video");
    const chunkStr = url.searchParams.get("chunk");
    if (!videoName || !chunkStr) {
        res.writeHead(400);
        return res.end();
    }

    const cachedVideo = videoCache[videoName];
    if (!cachedVideo) {
        res.writeHead(200, { "Content-Type": "application/octet-stream" });
        return res.end(Buffer.alloc(FRAME_SIZE));
    }

    const chunkNum = parseInt(chunkStr, 10);
    const startFrame = chunkNum * CHUNK_SIZE;

    if (startFrame >= cachedVideo.totalFrames) {
        res.writeHead(200, { "Content-Type": "application/octet-stream" });
        return res.end(Buffer.alloc(0)); // End of video signal
    }

    const startByte = startFrame * FRAME_SIZE;
    let endFrame = startFrame + CHUNK_SIZE;
    if (endFrame > cachedVideo.totalFrames) endFrame = cachedVideo.totalFrames;
    const endByte = endFrame * FRAME_SIZE;

    res.writeHead(200, { "Content-Type": "application/octet-stream" });
    res.end(cachedVideo.buffer.subarray(startByte, endByte));
});

server.listen(PORT);
