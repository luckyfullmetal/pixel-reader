import http from 'http';
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';

const WIDTH = 181;
const HEIGHT = 102;
const FRAME_SIZE = WIDTH * HEIGHT * 3;
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
    const frameStr = url.searchParams.get("frame");
    if (!videoName || !frameStr) {
        res.writeHead(400);
        return res.end();
    }

    const cachedVideo = videoCache[videoName];
    if (!cachedVideo) {
        res.writeHead(200, { "Content-Type": "application/octet-stream" });
        return res.end(Buffer.alloc(FRAME_SIZE));
    }

    const frameNum = parseInt(frameStr, 10);
    if (frameNum >= cachedVideo.totalFrames) {
        res.writeHead(200, { "Content-Type": "application/octet-stream" });
        return res.end(Buffer.alloc(0));
    }

    const startByte = frameNum * FRAME_SIZE;
    res.writeHead(200, { "Content-Type": "application/octet-stream" });
    res.end(cachedVideo.buffer.subarray(startByte, startByte + FRAME_SIZE));
});

server.listen(PORT);
