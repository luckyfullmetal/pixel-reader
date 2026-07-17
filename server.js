import { spawn } from "bun";

const WIDTH = 181;
const HEIGHT = 102;
const FRAME_SIZE = WIDTH * HEIGHT * 3; // 3 bytes per pixel (RGB)

Bun.serve({
  port: process.env.PORT || 8080,
  async fetch(req) {
    const url = new URL(req.url);
    
    if (url.pathname !== "/stream") {
      return new Response("Not Found", { status: 404 });
    }

    const videoName = url.searchParams.get("video");
    const frameStr = url.searchParams.get("frame");

    if (!videoName || !frameStr) {
      return new Response("Missing parameters", { status: 400 });
    }

    const frameNum = parseInt(frameStr, 10);
    const timePosition = (frameNum / 30).toFixed(4); // 30 FPS video

    const ffmpeg = spawn([
      "ffmpeg",
      "-ss", timePosition,
      "-i", videoName,
      "-vframes", "1",
      "-vf", `scale=${WIDTH}:${HEIGHT}:flags=neighbor`, // Nearest-neighbor scaling
      "-f", "rawvideo",
      "-pix_fmt", "rgb24",
      "pipe:1"
    ], {
      stdout: "pipe",
      stderr: "ignore"
    });

    const responseBuffer = await new Response(ffmpeg.stdout).arrayBuffer();
    const uint8Array = new Uint8Array(responseBuffer);

    if (uint8Array.length < FRAME_SIZE) {
      return new Response(new Uint8Array(0), {
        headers: { "Content-Type": "application/octet-stream" }
      });
    }

    return new Response(uint8Array, {
      headers: { "Content-Type": "application/octet-stream" }
    });
  }
});

console.log("Bare-metal Bun server listening...");
