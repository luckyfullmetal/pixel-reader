package main

import (
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
)

const FrameSize = 181 * 102 * 3

func main() {
	files, err := os.ReadDir(".")
	if err == nil {
		for _, f := range files {
			if filepath.Ext(f.Name()) == ".mp4" {
				out, _ := os.Create(f.Name()[:len(f.Name())-4] + ".bin")
				cmd := exec.Command("ffmpeg", "-y", "-i", f.Name(), "-vf", "scale=181:102:flags=neighbor", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1")
				cmd.Stdout = out
				cmd.Run()
				out.Close()
			}
		}
	}

	http.HandleFunc("/download", func(w http.ResponseWriter, r *http.Request) {
		vid := r.URL.Query().Get("video")
		if vid == "" {
			return
		}
		file, err := os.Open(vid + ".bin")
		if err != nil {
			return
		}
		defer file.Close()
		w.Header().Set("Content-Type", "application/octet-stream")
		io.Copy(w, file)
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	http.ListenAndServe(":"+port, nil)
}
