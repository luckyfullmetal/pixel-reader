import os
import struct
import cv2

TARGET_WIDTH = 384
TARGET_HEIGHT = 216
# Increase this step value if your file is still slightly over 100MB (e.g., to 6 or 7)
FRAME_STEP = 5 

def process_video(file_path):
    video_name = os.path.splitext(file_path)[0]
    cap = cv2.VideoCapture(file_path)
    
    if not cap.isOpened():
        print(f"Failed to open {file_path}")
        return

    # Calculate original source video statistics
    source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    file_fps = source_fps / FRAME_STEP

    frame_count = 0
    raw_frame_index = 0
    raw_binary_data = bytearray()

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Temporal compression pass
        if raw_frame_index % FRAME_STEP == 0:
            resized = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_NEAREST)
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            
            raw_binary_data.extend(rgb_frame.flatten().tobytes())
            frame_count += 1
            
        raw_frame_index += 1

    cap.release()

    # 12-byte binary layout header:
    # 4 bytes total frames (uint32), 2 bytes width (uint16), 2 bytes height (uint16), 4 bytes file_fps (float)
    header = struct.pack("<IHHf", frame_count, TARGET_WIDTH, TARGET_HEIGHT, file_fps)
    
    output_filename = f"{video_name}.bin"
    with open(output_filename, "wb") as f:
        f.write(header + raw_binary_data)
        
    print(f"Generated binary {output_filename} ({frame_count} frames) at {TARGET_WIDTH}x{TARGET_HEIGHT}!")
    print(f"Target Playback Speed: {file_fps:.2f} FPS")

for file in os.listdir('.'):
    if file.endswith('.mp4'):
        process_video(file)
