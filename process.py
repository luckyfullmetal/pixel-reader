import os
import cv2

TARGET_WIDTH = 256
TARGET_HEIGHT = 144
FRAME_STEP = 2 # Skips every other frame to keep 256x144 safely under 100MB text limit

def process_video(file_path):
    video_name = os.path.splitext(file_path)[0]
    cap = cv2.VideoCapture(file_path)
    
    if not cap.isOpened():
        print(f"Failed to open {file_path}")
        return

    frame_count = 0
    raw_frame_index = 0
    hex_frames = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if raw_frame_index % FRAME_STEP == 0:
            resized = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_NEAREST)
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            
            # Convert RGB values into your direct 6-character hex string format
            frame_hex = []
            for row in rgb_frame:
                for pixel in row:
                    frame_hex.append(f"{pixel[0]:02x}{pixel[1]:02x}{pixel[2]:02x}")
            
            hex_frames.append("".join(frame_hex))
            frame_count += 1
            
        raw_frame_index += 1

    cap.release()

    # Build the header line matching your exact string format split logic
    header = f"{frame_count},{TARGET_WIDTH},{TARGET_HEIGHT}\n"
    full_payload = header + "".join(hex_frames)
    
    output_filename = f"{video_name}.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(full_payload)
        
    print(f"Generated text stream {output_filename} ({frame_count} frames) at {TARGET_WIDTH}x{TARGET_HEIGHT}!")

for file in os.listdir('.'):
    if file.endswith('.mp4'):
        process_video(file)
