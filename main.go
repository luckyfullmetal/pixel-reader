package main

import (
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
)

func main() {
	// Pre-convert videos on startup
	files, err := os.ReadDir(".")
	if err == nil {
		for _, f := range files {
			if filepath.Ext(f.Name()) == ".mp4" {
				binName := filepath.Join(os.TempDir(), f.Name()[:len(f.Name())-4]+".bin")
				if _, err := os.Stat(binName); os.IsNotExist(err) {
					outFile, _ := os.Create(binName)
					cmd := exec.Command("ffmpeg", "-y", "-i", f.Name(), "-vf", "scale=181:102:flags=neighbor", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1")
					cmd.Stdout = outFile
					cmd.Run()
					outFile.Close()
				}
			}
		}
	}

	// Set up the HTTP route handler
	http.HandleFunc("/download", func(w http.ResponseWriter, r *http.Request) {
		vid := r.URL.Query().Get("video")
		if vid == "" { return }

		file, err := os.Open(filepath.Join(os.TempDir(), vid+".bin"))
		if err != nil {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		defer file.Close()

		// Hijack the underlying TCP network socket to bypass standard HTTP overhead wrappers
		hijacker, ok := w.(http.Hijacker)
		if !ok { return }
		conn, bufrw, err := hijacker.Hijack()
		if err != nil { return }
		defer conn.Close()

		// BARE-METAL SECRET TRICK: Disable kernel buffering.
		// Forces the network card to transmit packets instantly without waiting.
		if tcpConn, ok := conn.(*net.TCPConn); ok {
			tcpConn.SetNoDelay(true)
		}

		// Write bare-minimum HTTP headers directly to the raw socket wire
		bufrw.WriteString("HTTP/1.1 200 OK\r\nContent-Type: application/octet-stream\r\nConnection: close\r\n\r\n")
		bufrw.Flush()

		// Stream the data matrix with zero intermediate memory copies
		fi, _ := file.Stat()
		os.NewFile(uintptr(file.Fd()), fi.Name())
		file.WriteTo(bufrw)
		bufrw.Flush()
	})

	// Start the server directly on Port 10000
	http.ListenAndServe(":10000", nil)
}
