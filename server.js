import http from 'http';
import { spawn } from 'child_process';

const WIDTH = 181;
const HEIGHT = 102;
const FRAME_SIZE = WIDTH * HEIGHT * 3; // 3 bytes per pixel (RGB)
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

    const frameNum = parseInt(frameStr, 10);
    const timePosition = (frameNum / 30).toFixed(4); // Assuming 30 FPS video

    // Bare-metal spawn of ffmpeg via Node.js
    const ffmpeg = spawn("ffmpeg", [
        "-ss", timePosition,
        "-i", videoName,
        "-vframes", "1",
        "-vf", `scale=${WIDTH}:${HEIGHT}:flags=neighbor`, // Nearest-neighbor scaling
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "pipe:1"
    ]);

    let buffers = [];

    ffmpeg.stdout.on('data', (chunk) => {
        buffers.push(chunk);
    });

    ffmpeg.on('close', () => {
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
