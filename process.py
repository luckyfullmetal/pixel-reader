import os
import json
import cv2

TARGET_WIDTH = 181
TARGET_HEIGHT = 102

def process_video(file_path):
    video_name = os.path.splitext(file_path)[0]
    cap = cv2.VideoCapture(file_path)
    
    if not cap.isOpened():
        print(f"Failed to open {file_path}")
        return

    flat_pixel_data = []
    frame_count = 0
    raw_frame_index = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Skip every second frame to stay safely within limits
        if raw_frame_index % 2 == 0:
            resized = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_NEAREST)
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            
            # Flatten frame to R,G,B elements
            flat_pixel_data.extend(rgb_frame.flatten().tolist())
            frame_count += 1
            
        raw_frame_index += 1

    cap.release()

    payload = {
        "frames": frame_count,
        "width": TARGET_WIDTH,
        "height": TARGET_HEIGHT,
        "data": flat_pixel_data
    }
    
    output_filename = f"{video_name}.json"
    with open(output_filename, "w") as f:
        json.dump(payload, f)
        
    print(f"Generated {output_filename} ({frame_count} frames)")

for file in os.listdir('.'):
    if file.endswith('.mp4'):
        process_video(file)
