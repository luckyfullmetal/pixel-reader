package main

import (
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
)

func main() {
	// Pre-build binary frames on system initialization
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

	http.HandleFunc("/download", func(w http.ResponseWriter, r *http.Request) {
		vid := r.URL.Query().Get("video")
		if vid == "" { return }

		file, err := os.Open(filepath.Join(os.TempDir(), vid+".bin"))
		if err != nil {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		defer file.Close()

		// SOTW (Speed of the Wire): Hijack the raw connection socket
		hijacker, ok := w.(http.Hijacker)
		if !ok { return }
		conn, bufrw, err := hijacker.Hijack()
		if err != nil { return }
		defer conn.Close()

		// Disable Nagle's algorithm entirely to guarantee data drops into the network wire instantaneously
		if tcpConn, ok := conn.(*net.TCPConn); ok {
			tcpConn.SetNoDelay(true)
		}

		// Minimum required characters for an HTTP response packet
		bufrw.WriteString("HTTP/1.1 200 OK\r\nContent-Type: application/octet-stream\r\nConnection: close\r\n\r\n")
		bufrw.Flush()

		// Directly link the file descriptor to the socket pipeline
		file.WriteTo(bufrw)
		bufrw.Flush()
	})

	http.ListenAndServe(":10000", nil)
}
