import http from 'http';
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';

const WIDTH = 181;
const HEIGHT = 102;
const FRAME_SIZE = WIDTH * HEIGHT * 3; // 55,386 bytes per frame
const PORT = process.env.PORT || 8080;

const videoCache = {};

// Function to convert MP4 to a raw binary file, or load it if it already exists
function prepareRawData(videoFile) {
    const ext = path.extname(videoFile);
    const baseName = path.basename(videoFile, ext);
    const binFile = `${baseName}.bin`;

    // 1. If the raw binary cache file already exists, load it instantly bare-metal
    if (fs.existsSync(binFile)) {
        console.log(`[Cache] Found pre-converted data file: ${binFile}. Loading straight to RAM...`);
        const fullBuffer = fs.readFileSync(binFile);
        const totalFrames = Math.floor(fullBuffer.length / FRAME_SIZE);
        
        videoCache[videoFile] = { buffer: fullBuffer, totalFrames };
        console.log(`[Cache] Loaded ${totalFrames} frames from ${binFile} directly into RAM.`);
        return;
    }

    // 2. If it doesn't exist, convert the MP4 to raw binary color data right now
    console.log(`[Converter] ${binFile} not found. Baking MP4 into raw color binary data...`);
    
    const ffmpeg = spawn("ffmpeg", [
        "-i", videoFile,
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
        if (code !== 0) {
            console.error(`[Converter] Failed to convert ${videoFile}`);
            return;
        }

        const fullBuffer = Buffer.concat(buffers);
        const totalFrames = Math.floor(fullBuffer.length / FRAME_SIZE);

        // Save it to disk so the next time the server starts, it skips this entirely!
        fs.writeFileSync(binFile, fullBuffer);
        
        videoCache[videoFile] = { buffer: fullBuffer, totalFrames };
        console.log(`[Converter] Successfully created and cached ${binFile} (${(fullBuffer.length / 1024 / 1024).toFixed(2)} MB)`);
    });
}

// Automatically scan and process all MP4s in your root folder
fs.readdirSync('.').forEach(file => {
    if (file.endsWith('.mp4')) {
        prepareRawData(file);
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

    if (!cachedVideo) {
        res.writeHead(200, { "Content-Type": "application/octet-stream" });
        return res.end(Buffer.alloc(FRAME_SIZE));
    }

    const frameNum = parseInt(frameStr, 10);
    
    // Loop signal if video finishes
    if (frameNum >= cachedVideo.totalFrames) {
        res.writeHead(200, { "Content-Type": "application/octet-stream" });
        return res.end(Buffer.alloc(0));
    }

    // Direct memory pointer slice — highest execution speed possible in Node
    const startByte = frameNum * FRAME_SIZE;
    const frameBuffer = cachedVideo.buffer.subarray(startByte, startByte + FRAME_SIZE);

    res.writeHead(200, { "Content-Type": "application/octet-stream" });
    res.end(frameBuffer);
});

server.listen(PORT, () => {
    console.log(`Bare-metal direct RAM/Disk cache server listening on port ${PORT}`);
});
