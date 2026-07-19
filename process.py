import os
import struct
import cv2

TARGET_WIDTH = 384
TARGET_HEIGHT = 216

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
        
        # Keep 15 FPS to fit performance limits
        if raw_frame_index % 2 == 0:
            resized = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_NEAREST)
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            
            raw_binary_data.extend(rgb_frame.flatten().tobytes())
            frame_count += 1
            
        raw_frame_index += 1

    cap.release()

    # 8-byte binary layout header
    header = struct.pack("<IHH", frame_count, TARGET_WIDTH, TARGET_HEIGHT)
    
    output_filename = f"{video_name}.bin"
    with open(output_filename, "wb") as f:
        f.write(header + raw_binary_data)
        
    print(f"Generated binary {output_filename} ({frame_count} frames) at {TARGET_WIDTH}x{TARGET_HEIGHT}!")

for file in os.listdir('.'):
    if file.endswith('.mp4'):
        process_video(file)
