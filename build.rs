use std::process::Command;
use std::path::Path;

fn main() {
    println!("cargo:rerun-if-changed=OLED_TEST.mp4");

    if Path::new("OLED_TEST.mp4").exists() {
        // Instant hardware downscale using nearest-neighbor optimization
        let _ = Command::new("ffmpeg")
            .args([
                "-i", "OLED_TEST.mp4",
                "-vf", "scale=181:102:flags=neighbor",
                "-f", "rawvideo",
                "-pix_fmt", "rgb24",
                "-y", "scaled_raw.tmp"
            ])
            .status();
            
        // Trigger Script 2 (The Color Stripper)
        let _ = Command::new("rustc")
            .args(["strip_color.rs", "-o", "strip_color"])
            .status();
            
        let _ = Command::new("./strip_color").status();
    }
}
