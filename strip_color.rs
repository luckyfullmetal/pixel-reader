use std::fs::File;
use std::io::{Read, Write};

fn main() {
    let mut file = File::open("scaled_raw.tmp")
        .expect("Failed to locate scaled frames");
    
    let mut raw_bytes = Vec::new();
    file.read_to_end(&mut raw_bytes).unwrap();

    // Raw array output with 0 bytes of framing or metadata
    let mut out_file = File::create("OLED_TEST.raw")
        .expect("Failed to write stripped color data");
    out_file.write_all(&raw_bytes).unwrap();
    
    // Clean up intermediate files
    let _ = std::fs::remove_file("scaled_raw.tmp");
}
