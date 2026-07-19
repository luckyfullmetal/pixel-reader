import os
import struct
import base64
import cv2

TARGET_WIDTH = 160
TARGET_HEIGHT = 90

def process_video(file_path):
    video_name = os.path.splitext(file_path)[0]
    cap = cv2.VideoCapture(file_path)
    
    if not cap.isOpened():
        print(f"Failed to open {file_path}")
        return

    frame_count = 0
    raw_frame_index = 0
    raw_binary_data = bytearray()

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Keep 15 FPS
        if raw_frame_index % 2 == 0:
            resized = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_NEAREST)
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            
            raw_binary_data.extend(rgb_frame.flatten().tobytes())
            frame_count += 1
            
        raw_frame_index += 1

    cap.release()

    # 8-byte direct binary header structure
    header = struct.pack("<IHH", frame_count, TARGET_WIDTH, TARGET_HEIGHT)
    full_binary = header + raw_binary_data
    
    # Encode to safe Base64 string so HttpService doesn't drop null characters
    b64_encoded = base64.b64encode(full_binary).decode('utf-8')
    
    # Save it as a standard .bin extension file containing the safe text string
    output_filename = f"{video_name}.bin"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(b64_encoded)
        
    print(f"Generated Base64 binary stream {output_filename} ({frame_count} frames) at {TARGET_WIDTH}x{TARGET_HEIGHT}!")

for file in os.listdir('.'):
    if file.endswith('.mp4'):
        process_video(file)
