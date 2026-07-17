import { spawn } from "bun";

const WIDTH = 181;
const HEIGHT = 102;
const FRAME_SIZE = WIDTH * HEIGHT * 3; // 3 bytes per pixel (RGB)

Bun.serve({
  port: process.env.PORT || 8080,
  async fetch(req) {
    const url = new URL(req.url);
    
    // Only handle requests on /stream
    if (url.pathname !== "/stream") {
      return new Response("Not Found", { status: 404 });
    }

    const videoName = url.searchParams.get("video");
    const frameStr = url.searchParams.get("frame");

    if (!videoName || !frameStr) {
      return new Response("Missing parameters", { status: 400 });
    }

    const frameNum = parseInt(frameStr, 10);
    const timePosition = (frameNum / 30).toFixed(4); // Assuming 30 FPS video

    // Spawn ffmpeg natively to extract raw 24-bit RGB stream directly
    const ffmpeg = spawn([
      "ffmpeg",
      "-ss", timePosition,
      "-i", videoName,
      "-vframes", "1",
      "-vf", `scale=${WIDTH}:${HEIGHT}:flags=neighbor`, // Absolute fastest nearest-neighbor scaling
      "-f", "rawvideo",
      "-pix_fmt", "rgb24",
      "pipe:1"
    ], {
      stdout: "pipe",
      stderr: "ignore"
    });

    // Read the binary stream array buffer directly out of stdout
    const responseBuffer = await new Response(ffmpeg.stdout).arrayBuffer();
    const uint8Array = new Uint8Array(responseBuffer);

    // Ensure it's a complete frame, otherwise send an empty signal to tell Roblox to loop
    if (uint8Array.length < FRAME_SIZE) {
      return new Response(new Uint8Array(0), {
        headers: { "Content-Type": "application/octet-stream" }
      });
    }

    // Return raw byte stream packets (e.g. 255 becomes binary 11111111)
    return new Response(uint8Array, {
      headers: { "Content-Type": "application/octet-stream" }
    });
  }
});

console.log("Bare-metal Bun server listening...");
