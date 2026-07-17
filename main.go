package main

import (
	"bytes"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
)

const (
	Width     = 181
	Height    = 102
	FrameSize = Width * Height * 3
)

type VideoData struct {
	Buffer []byte
}

var videoCache = make(map[string]VideoData)

func main() {
	// Search the root directory for any .mp4 files to process on startup
	files, err := os.ReadDir(".")
	if err == nil {
		for _, file := range files {
			if filepath.Ext(file.Name()) == ".mp4" {
				fmt.Printf("Processing video file: %s\n", file.Name())
				
				// Execute FFmpeg to scale and extract raw RGB24 binary pixel frames
				cmd := exec.Command("ffmpeg", "-i", file.Name(), "-vf", fmt.Sprintf("scale=%d:%d:flags=neighbor", Width, Height), "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1")
				var out bytes.Buffer
				cmd.Stdout = &out
				
				if err := cmd.Run(); err == nil {
					videoCache[file.Name()] = VideoData{Buffer: out.Bytes()}
					fmt.Printf("Successfully cached: %s (%d bytes)\n", file.Name(), out.Len())
				} else {
					fmt.Printf("FFmpeg failed to process %s: %v\n", file.Name(), err)
				}
			}
		}
	}

	// This endpoint serves the entire video payload at once for upfront local caching in Roblox
	http.HandleFunc("/download", func(w http.ResponseWriter, r *http.Request) {
		vid := r.URL.Query().Get("video")
		if vid == "" {
			w.WriteHeader(http.StatusBadRequest)
			w.Write([]byte("Missing 'video' query parameter"))
			return
		}

		cache, exists := videoCache[vid]
		if !exists {
			w.WriteHeader(http.StatusNotFound)
			w.Write([]byte("Video not found on server"))
			return
		}

		w.Header().Set("Content-Type", "application/octet-stream")
		w.WriteHeader(http.StatusOK)
		w.Write(cache.Buffer)
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	
	fmt.Printf("Server starting on port %s...\n", port)
	if err := http.ListenAndServe(":"+port, nil); err != nil {
		fmt.Printf("Server failed to start: %v\n", err)
	}
}
