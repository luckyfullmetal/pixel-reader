package main

import (
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"strconv"
)

func main() {
	http.HandleFunc("/stream", streamHandler)
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	log.Printf("Server listening on port %s", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}

func streamHandler(w http.ResponseWriter, r *http.Request) {
	videoName := r.URL.Query().Get("video")
	frameStr := r.URL.Query().Get("frame")
	if videoName == "" || frameStr == "" {
		http.Error(w, "Missing video or frame parameter", http.StatusBadRequest)
		return
	}

	frameNum, err := strconv.Atoi(frameStr)
	if err != nil {
		http.Error(w, "Invalid frame number", http.StatusBadRequest)
		return
	}

	// Calculate timestamp for the exact frame assuming 30fps
	timePosition := fmt.Sprintf("%.4f", float64(frameNum)/30.0)

	// Bare metal extraction: Seek to exact time, resize to 181x102, output raw 24-bit RGB bytes directly to stdout
	cmd := exec.Command("ffmpeg",
		"-ss", timePosition,
		"-i", videoName,
		"-vframes", "1",
		"-s", "181x102",
		"-f", "rawvideo",
		"-pix_fmt", "rgb24",
		"pipe:1",
	)

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		http.Error(w, "Server internal error", http.StatusInternalServerError)
		return
	}

	if err := cmd.Start(); err != nil {
		http.Error(w, "Failed to start ffmpeg", http.StatusInternalServerError)
		return
	}

	// Stream the raw bytes directly to Roblox's HTTP request
	w.Header().Set("Content-Type", "application/octet-stream")
	io.Copy(w, stdout)
	cmd.Wait()
}
