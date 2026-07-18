package main

import (
	"bytes"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"sync"
)

// Global in-memory cache to store raw binary frames directly in RAM
var (
	videoCache = make(map[string][]byte)
	cacheLock  sync.RWMutex
)

func main() {
	files, err := os.ReadDir(".")
	if err == nil {
		for _, f := range files {
			if filepath.Ext(f.Name()) == ".mp4" {
				baseName := f.Name()[:len(f.Name())-4]

				// Run FFmpeg and pipe the raw bytes straight into a RAM buffer instead of a file
				cmd := exec.Command("ffmpeg", "-y", "-i", f.Name(), "-vf", "scale=181:102:flags=neighbor", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1")
				
				var ramBuffer bytes.Buffer
				cmd.Stdout = &ramBuffer
				
				if err := cmd.Run(); err == nil {
					// Save the raw byte array directly into our global RAM map
					videoCache[baseName] = ramBuffer.Bytes()
				}
			}
		}
	}

	http.HandleFunc("/download", func(w http.ResponseWriter, r *http.Request) {
		vid := r.URL.Query().Get("video")
		if vid == "" { return }

		// Thread-safe memory lookup (blistering fast)
		cacheLock.RLock()
		data, exists := videoCache[vid]
		cacheLock.RUnlock()

		if !exists {
			w.WriteHeader(http.StatusNotFound)
			return
		}

		w.Header().Set("Content-Type", "application/octet-stream")
		// Directly stream the bytes from RAM straight to the network card pipeline
		w.Write(data)
	})

	port := os.Getenv("PORT")
	if port == "" { port = "8080" }
	http.ListenAndServe(":"+port, nil)
}
