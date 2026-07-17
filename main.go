package main

import (
	"bytes"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
)

const (
	Width     = 181
	Height    = 102
	FrameSize = Width * Height * 3
)

type VideoData struct {
	Buffer []byte
	Frames int
}

var videoCache = make(map[string]VideoData)

func main() {
	files, _ := os.ReadDir(".")
	for _, file := range files {
		if filepath.Ext(file.Name()) == ".mp4" {
			cmd := exec.Command("ffmpeg", "-i", file.Name(), "-vf", fmt.Sprintf("scale=%d:%d:flags=neighbor", Width, Height), "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1")
			var out bytes.Buffer
			cmd.Stdout = &out
			if cmd.Run() == nil {
				buf := out.Bytes()
				videoCache[file.Name()] = VideoData{Buffer: buf, Frames: len(buf) / FrameSize}
			}
		}
	}

	http.HandleFunc("/stream", func(w http.ResponseWriter, r *http.Request) {
		q := r.URL.Query()
		vid, fStr := q.Get("video"), q.Get("frame")
		if vid == "" || fStr == "" {
			w.WriteHeader(400)
			return
		}
		cache, exists := videoCache[vid]
		if !exists {
			w.WriteHeader(200)
			w.Write(make([]byte, FrameSize))
			return
		}
		fNum, _ := strconv.Atoi(fStr)
		if fNum >= cache.Frames {
			w.WriteHeader(200)
			w.Write(make([]byte, 0))
			return
		}
		start := fNum * FrameSize
		w.Header().Set("Content-Type", "application/octet-stream")
		w.Write(cache.Buffer[start : start+FrameSize])
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	http.ListenAndServe(":"+port, nil)
}
