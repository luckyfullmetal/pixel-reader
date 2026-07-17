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
	files, err := os.ReadDir(".")
	if err == nil {
		for _, f := range files {
			if filepath.Ext(f.Name()) == ".mp4" {
				baseName := f.Name()[:len(f.Name())-4]
				binFileName := filepath.Join(os.TempDir(), baseName+".bin")

				outFile, _ := os.Create(binFileName)
				
				// Temp buffer to hold the raw RGB stream from FFmpeg
				cmd := exec.Command("ffmpeg", "-y", "-i", f.Name(), "-vf", "scale=181:102:flags=neighbor", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1")
				pr, pw := io.Pipe()
				cmd.Stdout = pw
				
				go func() {
					cmd.Run()
					pw.Close()
				}()

				// Read 3 bytes at a time, pack into 4 bytes (RGBA format)
				rgb := make([]byte, 3)
				packed := make([]byte, 4)
				for {
					_, err := io.ReadFull(pr, rgb)
					if err == io.EOF || err == io.ErrUnexpectedEOF {
						break
					}
					// Pack R, G, B into an integer stream (Alpha is 255/fully opaque)
					packed[0] = rgb[0] // R
					packed[1] = rgb[1] // G
					packed[2] = rgb[2] // B
					packed[3] = 255    // A
					outFile.Write(packed)
				}
				outFile.Close()
			}
		}
	}

	http.HandleFunc("/download", func(w http.ResponseWriter, r *http.Request) {
		vid := r.URL.Query().Get("video")
		if vid == "" { return }
		file, err := os.Open(filepath.Join(os.TempDir(), vid+".bin"))
		if err != nil { return }
		defer file.Close()
		w.Header().Set("Content-Type", "application/octet-stream")
		io.Copy(w, file)
	})

	port := os.Getenv("PORT")
	if port == "" { port = "8080" }
	http.ListenAndServe(":"+port, nil)
}
