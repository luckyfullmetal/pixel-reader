import os
import cv2

TARGET_WIDTH = 640
TARGET_HEIGHT = 360

def process_video(file_path):
    video_name = os.path.splitext(file_path)[0]
    cap = cv2.VideoCapture(file_path)
    
    if not cap.isOpened():
        print(f"Failed to open {file_path}")
        return

    frame_count = 0
    raw_frame_index = 0
    hex_payloads = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Keep 15 FPS to optimize file weight
        if raw_frame_index % 2 == 0:
            resized = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_NEAREST)
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            
            # Pack every pixel into 6 hex characters (e.g. "ff0000" for Red)
            for pixel in rgb_frame.reshape(-1, 3):
                hex_payloads.append(f"{pixel[0]:02x}{pixel[1]:02x}{pixel[2]:02x}")
                
            frame_count += 1
            
        raw_frame_index += 1

    cap.release()

    # Create a small comma-separated header line followed by the giant hex block
    final_output = f"{frame_count},{TARGET_WIDTH},{TARGET_HEIGHT}\n" + "".join(hex_payloads)
    
    output_filename = f"{video_name}.json"
    with open(output_filename, "w") as f:
        f.write(final_output)
        
    print(f"Generated {output_filename} ({frame_count} frames) - Optimized text string!")

for file in os.listdir('.'):
    if file.endswith('.mp4'):
        process_video(file)
