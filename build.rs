use std::process::Command;
use std::path::Path;
use std::fs::File;
use std::io::{Read, Write};
use std::env;

fn main() {
    println!("cargo:rerun-if-changed=OLED_TEST.mp4");

    if Path::new("OLED_TEST.mp4").exists() {
        let out_dir = env::var("OUT_DIR").unwrap();
        let temp_scaled_path = Path::new(&out_dir).join("scaled_raw.tmp");
        
        // 1. NEAREST-NEIGHBOR ACCURATE DOWNSCALE
        let _ = Command::new("ffmpeg")
            .args([
                "-i", "OLED_TEST.mp4",
                "-vf", "scale=181:102:flags=neighbor",
                "-f", "rawvideo",
                "-pix_fmt", "rgb24",
                "-y",
                temp_scaled_path.to_str().unwrap()
            ])
            .status();
            
        // 2. STRIP ALL EXTRANEOUS DATA AWAY
        if temp_scaled_path.exists() {
            let mut file = File::open(&temp_scaled_path).unwrap();
            let mut raw_bytes = Vec::new();
            let _ = file.read_to_end(&mut raw_bytes);

            let final_raw_path = Path::new(&out_dir).join("OLED_TEST.raw");
            let mut out_file = File::create(final_raw_path).unwrap();
            let _ = out_file.write_all(&raw_bytes);

            let _ = std::fs::remove_file(temp_scaled_path);
        }
    }
}
