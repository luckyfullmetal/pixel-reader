import http from 'http';
import { spawn } from 'child_process';
import fs from 'fs';

const WIDTH = 181;
const HEIGHT = 102;
const FRAME_SIZE = WIDTH * HEIGHT * 3; // 55,386 bytes per frame
const PORT = process.env.PORT || 8080;

// This will cache our raw binary frame streams in RAM
const videoCache = {};

// Function to decode an entire MP4 into RAM on startup
function preLoadVideo(videoName) {
    if (!fs.existsSync(videoName)) {
        console.log(`[Cache] Skipping ${videoName} (File not found)`);
        return;
    }
    
    console.log(`[Cache] Pre-loading ${videoName} into memory...`);
    
    const ffmpeg = spawn("ffmpeg", [
        "-i", videoName,
        "-vf", `scale=${WIDTH}:${HEIGHT}:flags=neighbor`,
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "pipe:1"
    ]);

    let buffers = [];

    ffmpeg.stdout.on('data', (chunk) => {
        buffers.push(chunk);
    });

    ffmpeg.on('close', (code) => {
        const fullBuffer = Buffer.concat(buffers);
        const totalFrames = Math.floor(fullBuffer.length / FRAME_SIZE);
        
        videoCache[videoName] = {
            buffer: fullBuffer,
            totalFrames: totalFrames
        };
        console.log(`[Cache] Successfully loaded ${videoName}. Total frames in RAM: ${totalFrames} (${(fullBuffer.length / 1024 / 1024).toFixed(2)} MB)`);
    });
}

// Automatically scan and pre-load your videos when the server starts
const filesInRoot = fs.readdirSync('.');
filesInRoot.forEach(file => {
    if (file.endsWith('.mp4')) {
        preLoadVideo(file);
    }
});

const server = http.createServer((req, res) => {
    const url = new URL(req.url, `http://${req.headers.host}`);
    
    if (url.pathname !== "/stream") {
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        return res.end("Not Found");
    }

    const videoName = url.searchParams.get("video");
    const frameStr = url.searchParams.get("frame");

    if (!videoName || !frameStr) {
        res.writeHead(400, { 'Content-Type': 'text/plain' });
        return res.end("Missing parameters");
    }

    const cachedVideo = videoCache[videoName];

    // If the video hasn't loaded yet or doesn't exist, send a blank frame
    if (!cachedVideo) {
        res.writeHead(200, { "Content-Type": "application/octet-stream" });
        return res.end(Buffer.alloc(FRAME_SIZE));
    }

    const frameNum = parseInt(frameStr, 10);
    
    // If the requested frame exceeds video length, send empty body so Roblox loops
    if (frameNum >= cachedVideo.totalFrames) {
        res.writeHead(200, { "Content-Type": "application/octet-stream" });
        return res.end(Buffer.alloc(0));
    }

    // Instantly slice the exact 55KB frame data directly out of RAM
    const startByte = frameNum * FRAME_SIZE;
    const endByte = startByte + FRAME_SIZE;
    const frameBuffer = cachedVideo.buffer.subarray(startByte, endByte);

    res.writeHead(200, { "Content-Type": "application/octet-stream" });
    res.end(frameBuffer);
});

server.listen(PORT, () => {
    console.log(`High-speed RAM-cached Node server listening on port ${PORT}`);
});
