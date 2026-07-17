# Use official ultra-fast Bun image
FROM oven/bun:1-alpine

# Install FFmpeg for bare metal video decoding
RUN apk add --no-cache ffmpeg

WORKDIR /app

# Copy the server script and configuration
COPY package.json server.js ./

# Copy all your video files directly into the environment
COPY *.mp4 ./

# Run bun package install
RUN bun install

EXPOSE 8080

# Start the server bare metal
CMD ["bun", "run", "server.js"]
