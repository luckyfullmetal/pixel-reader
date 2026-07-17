import http from 'http';
import { spawn } from 'child_process';
import fs from 'fs';

const WIDTH = 181;
const HEIGHT = 102;
const FRAME_SIZE = WIDTH * HEIGHT * 3; 
const PORT = process.env.PORT || 8080;

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

    // CHECK IF FILE ACTUALLY EXISTS ON RENDER
    if (!fs.existsSync(videoName)) {
        console.error(`[ERROR] File not found in root directory: ${videoName}`);
        console.log("Available files:", fs.readdirSync('.'));
        res.writeHead(200, { "Content-Type": "application/octet-stream" });
        return res.end(Buffer.alloc(FRAME_SIZE)); // Send black frame so it doesn't crash
    }

    const frameNum = parseInt(frameStr, 10);
    const timePosition = (frameNum / 30).toFixed(4); 

    const ffmpeg = spawn("ffmpeg", [
        "-ss", timePosition,
        "-i", videoName,
        "-vframes", "1",
        "-vf", `scale=${WIDTH}:${HEIGHT}:flags=neighbor`, 
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "pipe:1"
    ]);

    let buffers = [];
    let errorLogs = "";

    ffmpeg.stdout.on('data', (chunk) => {
        buffers.push(chunk);
    });

    ffmpeg.stderr.on('data', (data) => {
        errorLogs += data.toString();
    });

    ffmpeg.on('close', (code) => {
        if (code !== 0) {
            console.error(`[FFmpeg Crashed] Code ${code}. Error logs:`, errorLogs);
            res.writeHead(200, { "Content-Type": "application/octet-stream" });
            return res.end(Buffer.alloc(FRAME_SIZE)); // Return blank black frame on crash
        }

        const responseBuffer = Buffer.concat(buffers);

        if (responseBuffer.length < FRAME_SIZE) {
            res.writeHead(200, { "Content-Type": "application/octet-stream" });
            return res.end(Buffer.alloc(0)); // Loop signal
        }

        res.writeHead(200, { "Content-Type": "application/octet-stream" });
        res.end(responseBuffer);
    });
});

server.listen(PORT, () => {
    console.log(`Bare-metal Node server listening on port ${PORT}`);
});
