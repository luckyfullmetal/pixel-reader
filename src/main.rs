use std::net::SocketAddr;
use std::sync::Arc;
use tokio::net::TcpListener;
use tokio::io::AsyncWriteExt;

const COLS: usize = 181;
const ROWS: usize = 102;
const CHUNK_SIZE: usize = 5; 
const FRAME_SIZE: usize = COLS * ROWS * 3;
const RESPONSE_SIZE: usize = FRAME_SIZE * CHUNK_SIZE;

// Video is baked straight into the running machine code!
const VIDEO_BYTES: &[u8] = include_bytes!(concat!(env!("OUT_DIR"), "/OLED_TEST.raw"));

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let addr: SocketAddr = "0.0.0.0:10000".parse()?;
    let listener = TcpListener::bind(&addr).await?;
    println!("Bare-metal server open on port 10000");
    
    let total_frames = VIDEO_BYTES.len() / FRAME_SIZE;
    let shared_buffer = Arc::new(VIDEO_BYTES);

    loop {
        let (mut socket, _) = listener.accept().await?;
        let buffer_ref = Arc::clone(&shared_buffer);

        tokio::spawn(async move {
            let mut read_buf = [0; 256];
            if let Ok(n) = socket.try_read(&mut read_buf) {
                let request_str = String::from_utf8_lossy(&read_buf[..n]);
                if let Some(frame_param) = request_str.split("frame=").nth(1) {
                    if let Some(frame_val) = frame_param.split(|c| c == ' ' || c == '&').next() {
                        if let Ok(start_frame) = frame_val.parse::<usize>() {
                            
                            let headers = format!(
                                "HTTP/1.1 200 OK\r\n\
                                 Content-Type: application/octet-stream\r\n\
                                 Content-Length: {}\r\n\
                                 Access-Control-Allow-Origin: *\r\n\
                                 Connection: close\r\n\r\n",
                                RESPONSE_SIZE
                            );

                            let mut payload = Vec::with_capacity(headers.len() + RESPONSE_SIZE);
                            payload.extend_from_slice(headers.as_bytes());

                            for i in 0..CHUNK_SIZE {
                                let current_frame = (start_frame + i) % total_frames;
                                let offset = current_frame * FRAME_SIZE;
                                payload.extend_from_slice(&buffer_ref[offset..offset + FRAME_SIZE]);
                            }

                            let _ = socket.write_all(&payload).await;
                        }
                    }
                }
            }
        });
    }
}
