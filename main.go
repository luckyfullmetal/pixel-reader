package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
)

const (
	Cols         = 181
	Rows         = 102
	ChunkSize    = 5
	FrameSize    = Cols * Rows * 3
	ResponseSize = FrameSize * ChunkSize
)

var (
	cache   = make(map[string][]byte)
	cacheMu sync.RWMutex
)

// Process the MP4 into raw bytes using FFmpeg on the fly
func getOrProcessVideo(name string) ([]byte, error) {
	cacheMu.RLock()
	data, exists := cache[name]
	cacheMu.RUnlock()
	if exists {
		return data, nil
	}

	cacheMu.Lock()
	defer cacheMu.Unlock()
	
	// Double check memory cache
	if data, exists = cache[name]; exists {
		return data, nil
	}

	mp4Path := fmt.Sprintf("%s.mp4", name)
	if _, err := os.Stat(mp4Path); os.IsNotExist(err) {
		return nil, fmt.Errorf("video file %s not found", mp4Path)
	}

	rawPath := fmt.Sprintf("%s.raw", name)
	
	// If it wasn't pre-processed, run a fast nearest-neighbor downscale strip
	if _, err := os.Stat(rawPath); os.IsNotExist(err) {
		fmt.Printf("Processing %s to raw format...\n", mp4Path)
		cmd := exec.Command("ffmpeg",
			"-i", mp4Path,
			"-vf", "scale=181:102:flags=neighbor",
			"-f", "rawvideo",
			"-pix_fmt", "rgb24",
			"-y",
			rawPath,
		)
		if err := cmd.Run(); err != nil {
			return nil, fmt.Errorf("ffmpeg failed: %v", err)
		}
	}

	// Read stripped raw bytes into high-speed memory cache
	rawBytes, err := os.ReadFile(rawPath)
	if err != nil {
		return nil, err
	}

	cache[name] = rawBytes
	fmt.Printf("Successfully cached %s (%d frames)\n", rawPath, len(rawBytes)/FrameSize)
	return rawBytes, nil
}

func handleFrameRequest(w http.ResponseWriter, r *http.Request) {
	// Enable CORS so Roblox can read the header streams safely
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Content-Type", "application/octet-stream")

	query := r.URL.Query()
	
	fileName := query.Get("file")
	if fileName == "" {
		fileName = "OLED_TEST"
	}
	// Sanitize path inputs
	fileName = filepath.Base(strings.TrimSuffix(fileName, ".mp4"))

	frameStr := query.Get("frame")
	startFrame, err := strconv.Atoi(frameStr)
	if err != nil {
		startFrame = 0
	}

	videoBytes, err := getOrProcessVideo(fileName)
	if err != nil {
		http.Error(w, err.Error(), http.StatusNotFound)
		return
	}

	totalFrames := len(videoBytes) / FrameSize
	if totalFrames == 0 {
		http.Error(w, "Video contains no frame data", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Length", strconv.Itoa(ResponseSize))
	w.WriteHeader(http.StatusOK)

	// Direct pointer-like slice extraction to feed the network socket instantly
	payload := make([]byte, 0, ResponseSize)
	for i := 0; i < ChunkSize; i++ {
		currentFrame := (startFrame + i) % totalFrames
		offset := currentFrame * FrameSize
		payload = append(payload, videoBytes[offset:offset+FrameSize]...)
	}

	w.Write(payload)
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "10000"
	}

	http.HandleFunc("/", handleFrameRequest)

	fmt.Printf("Go dynamic server listening instantly on port %s...\n", port)
	log.Fatal(http.ListenAndServe(":" + port, nil))
}
