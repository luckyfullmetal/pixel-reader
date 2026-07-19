import os
import struct
import cv2
import base64

TARGET_WIDTH = 181
TARGET_HEIGHT = 102

def process_video(file_path):
    video_name = os.path.splitext(file_path)[0]
    cap = cv2.VideoCapture(file_path)
    
    if not cap.isOpened():
        print(f"Failed to open {file_path}")
        return

    frames_bytes = bytearray()
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Downscale using Nearest Neighbor
        resized = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_NEAREST)
        # OpenCV reads BGR; convert to RGB
        rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        frames_bytes.extend(rgb_frame.tobytes())
        frame_count += 1

    cap.release()

    # Binary Header: Frame Count (4 bytes), Width (2 bytes), Height (2 bytes)
    header = struct.pack("<IHH", frame_count, TARGET_WIDTH, TARGET_HEIGHT)
    full_payload = header + frames_bytes
    
    # Encode the raw binary into safe Base64 text
    b64_payload = base64.b64encode(full_payload)
    
    # Save as a .bin file containing pure text
    output_filename = f"{video_name}.bin"
    with open(output_filename, "wb") as f:
        f.write(b64_payload)
        
    print(f"Generated Roblox-compatible {output_filename} ({frame_count} frames)")

for file in os.listdir('.'):
    if file.endswith('.mp4'):
        process_video(file)
