import os
import cv2
import base91

TARGET_WIDTH = 181
TARGET_HEIGHT = 102

def process_video(file_path):
    video_name = os.path.splitext(file_path)[0]
    cap = cv2.VideoCapture(file_path)
    
    if not cap.isOpened():
        print(f"Failed to open {file_path}")
        return

    frame_count = 0
    raw_frame_index = 0
    raw_bytes = bytearray()

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if raw_frame_index % 2 == 0:
            resized = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_NEAREST)
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            
            for pixel in rgb_frame.reshape(-1, 3):
                raw_bytes.extend([pixel[0], pixel[1], pixel[2]])
                
            frame_count += 1
        raw_frame_index += 1

    cap.release()

    b91_string = base91.encode(raw_bytes)
    final_output = f"{frame_count},{TARGET_WIDTH},{TARGET_HEIGHT}\n{b91_string}"
    
    output_filename = f"{video_name}.json"
    with open(output_filename, "w") as f:
        f.write(final_output)
        
    print(f"Generated {output_filename} ({frame_count} frames) -> Lossless Base91!")

for file in os.listdir('.'):
    if file.endswith('.mp4'):
        process_video(file)
