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
	// Look for MP4s in the current application folder
	files, err := os.ReadDir(".")
	if err == nil {
		for _, file := range files {
			if filepath.Ext(file.Name()) == ".mp4" {
				baseName := file.Name()[:len(file.Name())-4]
				
				// We write to /tmp/ to ensure we have absolute write permissions on Render
				binFileName := filepath.Join(os.TempDir(), baseName+".bin")

				fmt.Printf("[CRT SERVER] Processing video file: %s -> Output: %s\n", file.Name(), binFileName)

				// Create the binary file in the temp directory
				outFile, err := os.Create(binFileName)
				if err != nil {
					fmt.Printf("[CRT SERVER] Error creating file %s: %v\n", binFileName, err)
					continue
				}

				// Run FFmpeg and stream directly to disk to keep RAM usage at 0
				cmd := exec.Command("ffmpeg", "-y", "-i", file.Name(), "-vf", fmt.Sprintf("scale=%d:%d:flags=neighbor", Width, Height), "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1")
				cmd.Stdout = outFile
				cmd.Stderr = os.Stderr // Pipes FFmpeg internal logs directly into your Render console logs!

				if err := cmd.Run(); err == nil {
					fmt.Printf("[CRT SERVER] Successfully created data disk cache: %s\n", binFileName)
				} else {
					fmt.Printf("[CRT SERVER] FFmpeg build execution failed for %s: %v\n", file.Name(), err)
				}
				outFile.Close()
			}
		}
	} else {
		fmt.Printf("[CRT SERVER] Failed to read repository directory: %v\n", err)
	}

	// Stream endpoint for Roblox to consume
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
		
		binFileName := filepath.Join(os.TempDir(), baseName+".bin")
		fmt.Printf("[CRT SERVER] Roblox requested download for: %s\n", binFileName)

		file, err := os.Open(binFileName)
		if err != nil {
			fmt.Printf("[CRT SERVER] Roblox request failed: File not found: %s\n", binFileName)
			w.WriteHeader(http.StatusNotFound)
			w.Write([]byte("Video data cache file missing"))
			return
		}
		defer file.Close()

		w.Header().Set("Content-Type", "application/octet-stream")
		w.WriteHeader(http.StatusOK)
		
		io.Copy(w, file)
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	
	fmt.Printf("[CRT SERVER] Server live on port %s\n", port)
	if err := http.ListenAndServe(":"+port, nil); err != nil {
		fmt.Printf("[CRT SERVER] Server startup fatal error: %v\n", err)
	}
}
