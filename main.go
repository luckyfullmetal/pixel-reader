package main

import (
	"bytes"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/gofiber/fiber/v2"
)

// Global RAM cache for pre-baked 1D frames
var Videos = make(map[string][][]byte)

const (
	Cols = 181
	Rows = 102
	FrameSize = Cols * Rows * 3 // Width * Height * 3 bytes (RGB)
)

func preConvertVideos() {
	fmt.Println("--- STARTING 1D ULTRA-CONVERSION (GO + FFMPEG) ---")
	currDir, err := os.Getwd()
	if err != nil {
		log.Fatalf("Failed to get current directory: %v", err)
	}

	files, err := os.ReadDir(currDir)
	if err != nil {
		log.Fatalf("Failed to read directory: %v", err)
	}

	for _, f := range files {
		filename := f.Name()
		if !strings.HasSuffix(strings.ToLower(filename), ".mp4") {
			continue
		}

		videoPath := filepath.Join(currDir, filename)
		
		// Call FFmpeg to scale and output RAW 1D RGB24 bytes directly to standard output
		cmd := exec.Command("ffmpeg",
			"-i", videoPath,
			"-vf", fmt.Sprintf("scale=%d:%d:flags=neighbor", Cols, Rows),
			"-f", "rawvideo",
			"-pix_fmt", "rgb24",
			"pipe:1",
		)

		var outBuf bytes.Buffer
		cmd.Stdout = &outBuf
		cmd.Stderr = nil // Purge logs for maximum speed

		err := cmd.Run()
		if err != nil {
			fmt.Printf("[ERROR] Failed to decode %s: %v\n", filename, err)
			continue
		}

		rawBytes := outBuf.Bytes()
		totalFrames := len(rawBytes) / FrameSize

		var frames [][]byte
		for i := 0; i < totalFrames; i++ {
			start := i * FrameSize
			end := start + FrameSize
			
			// Extract flat frame slice and allocate
			frameData := make([]byte, FrameSize)
			copy(frameData, rawBytes[start:end])
			frames = append(frames, frameData)
		}

		Videos[filename] = frames
		fmt.Printf("[SUCCESS] Cooked '%s' (%d frames) into Go 1D RAM arrays.\n", filename, len(frames))
	}
	fmt.Println("--- GO DEMON SERVER READY: ZERO RUNTIME OVERHEAD ---")
}

func main() {
	preConvertVideos()

	app := fiber.New(fiber.Config{
		DisableStartupMessage: true,
	})

	// Absolute bare-bones route matching Roblox script
	app.Get("/get-frame/:filename/:frame_idx", func(c *fiber.Ctx) error {
		filename := c.Params("filename")
		
		vList, exists := Videos[filename]
		if !exists {
			return c.Status(404).SendString("404")
		}

		frameIdx, err := strconv.Atoi(c.Params("frame_idx"))
		if err != nil || frameIdx < 0 {
			frameIdx = 0
		}

		c.Set("Content-Type", "application/octet-stream")
		return c.Send(vList[frameIdx%len(vList)])
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "5000"
	}
	log.Fatal(app.Listen(":" + port))
}
