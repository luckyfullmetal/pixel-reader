package main

import (
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
)

func main() {
	ff, _ := os.ReadDir(".")
	for _, f := range ff {
		if filepath.Ext(f.Name()) == ".mp4" {
			out := filepath.Join(os.TempDir(), f.Name()[:len(f.Name())-4]+".bin")
			if _, err := os.Stat(out); os.IsNotExist(err) {
				fOut, _ := os.Create(out)
				// Raw pixel extraction down to exactly 181x102 layout dimensions
				c := exec.Command("ffmpeg", "-y", "-i", f.Name(), "-vf", "scale=181:102:flags=neighbor", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1")
				c.Stdout = fOut
				c.Run()
				fOut.Close()
			}
		}
	}

	http.HandleFunc("/download", func(w http.ResponseWriter, r *http.Request) {
		vid := r.URL.Query().Get("video")
		if vid == "" { return }

		f, err := os.Open(filepath.Join(os.TempDir(), vid+".bin"))
		if err != nil { return }
		defer f.Close()

		w.Header().Set("Content-Type", "application/octet-stream")
		fi, _ := f.Stat()
		
		// Streams the file contents directly as an optimized, continuous serial byte array
		http.ServeContent(w, r, vid+".bin", fi.ModTime(), f)
	})

	p := os.Getenv("PORT")
	if p == "" { p = "10000" }
	http.ListenAndServe(":"+p, nil)
}
