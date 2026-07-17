package main

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
)

const (
	Width  = 181
	Height = 102
)

func main() {
	// Process videos on startup without keeping them in RAM
	files, err := os.ReadDir(".")
	if err == nil {
		for _, file := range files {
			if filepath.Ext(file.Name()) == ".mp4" {
				baseName := file.Name()[:len(file.Name())-4]
				binFileName := baseName + ".bin"

				// Skip processing if we already generated the bin file previously
				if _, err := os.Stat(binFileName); err == nil {
					fmt.Printf("Found existing raw data file: %s\n", binFileName)
					continue
				}

				fmt.Printf("Processing video file to disk: %s -> %s\n", file.Name(), binFileName)

				// Create the output file on disk
				outFile, err := os.Create(binFileName)
				if err != nil {
					fmt.Printf("Failed to create file %s: %v\n", binFileName, err)
					continue
				}

				// Run FFmpeg and stream its output directly to the file on disk (0 RAM usage!)
				cmd := exec.Command("ffmpeg", "-i", file.Name(), "-vf", fmt.Sprintf("scale=%d:%d:flags=neighbor", Width, Height), "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1")
				cmd.Stdout = outFile

				if err := cmd.Run(); err == nil {
					fmt.Printf("Successfully created disk cache: %s\n", binFileName)
				} else {
					fmt.Printf("FFmpeg failed for %s: %v\n", file.Name(), err)
				}
				outFile.Close()
			}
		}
	}

	// Stream the file chunk-by-chunk to Roblox when requested
	http.HandleFunc("/download", func(w http.ResponseWriter, r *http.Request) {
		vid := r.URL.Query().Get("video")
		if vid == "" {
			w.WriteHeader(http.StatusBadRequest)
			w.Write([]byte("Missing 'video' query parameter"))
			return
		}

		baseName := vid
		if filepath.Ext(vid) == ".mp4" {
			baseName = vid[:len(vid)-4]
		}
		binFileName := baseName + ".bin"

		file, err := os.Open(binFileName)
		if err != nil {
			w.WriteHeader(http.StatusNotFound)
			w.Write([]byte("Video raw data file not found"))
			return
		}
		defer file.Close()

		w.Header().Set("Content-Type", "application/octet-stream")
		w.WriteHeader(http.StatusOK)
		
		// io.Copy streams the file straight to the network response in tiny 32KB chunks
		io.Copy(w, file)
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
