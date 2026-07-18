package main

import (
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
)

func main() {
	// 1. Pre-convert MP4s to standard files on disk to save RAM during runtime
	files, err := os.ReadDir(".")
	if err == nil {
		for _, f := range files {
			if filepath.Ext(f.Name()) == ".mp4" {
				baseName := f.Name()[:len(f.Name())-4]
				binFileName := filepath.Join(os.TempDir(), baseName+".bin")

				// If it doesn't exist yet, convert it once
				if _, err := os.Stat(binFileName); os.IsNotExist(err) {
					outFile, _ := os.Create(binFileName)
					cmd := exec.Command("ffmpeg", "-y", "-i", f.Name(), "-vf", "scale=181:102:flags=neighbor", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1")
					cmd.Stdout = outFile
					cmd.Run()
					outFile.Close()
				}
			}
		}
	}

	// 2. High-speed disk streaming with zero memory footprint
	http.HandleFunc("/download", func(w http.ResponseWriter, r *http.Request) {
		vid := r.URL.Query().Get("video")
		if vid == "" { return }

		file, err := os.Open(filepath.Join(os.TempDir(), vid+".bin"))
		if err != nil {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		defer file.Close()

		w.Header().Set("Content-Type", "application/octet-stream")
		
		// http.ServeContent automatically handles high-speed chunked disk transfers 
		// with optimal kernel-level buffering, bypassing Go's RAM allocation completely.
		fi, _ := file.Stat()
		http.ServeContent(w, r, vid+".bin", fi.ModTime(), file)
	})

	port := os.Getenv("PORT")
	if port == "" { port = "8080" }
	http.ListenAndServe(":"+port, nil)
}
