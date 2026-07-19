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
    compressed_payload = bytearray()
    
    prev_frame = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if raw_frame_index % 2 == 0:
            resized = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_NEAREST)
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            flat_frame = rgb_frame.reshape(-1, 3)
            
            if prev_frame is None:
                # First frame: Write ALL pixels out
                for pixel in flat_frame:
                    compressed_payload.extend([pixel[0], pixel[1], pixel[2]])
            else:
                # Sub-sequent frames: Find pixel index deltas
                diff_bytes = bytearray()
                for idx, pixel in enumerate(flat_frame):
                    prev_pixel = prev_frame[idx]
                    # Check if pixel color changed
                    if pixel[0] != prev_pixel[0] or pixel[1] != prev_pixel[1] or pixel[2] != prev_pixel[2]:
                        # Store index (2 bytes) + R, G, B (3 bytes)
                        diff_bytes.extend(idx.to_bytes(2, byteorder='big'))
                        diff_bytes.extend([pixel[0], pixel[1], pixel[2]])
                
                # Write marker of how many updates occurred in this frame (4 bytes)
                num_updates = len(diff_bytes) // 5
                compressed_payload.extend(num_updates.to_bytes(4, byteorder='big'))
                compressed_payload.extend(diff_bytes)

            prev_frame = flat_frame
            frame_count += 1
        raw_frame_index += 1

    cap.release()

    b91_string = base91.encode(compressed_payload)
    final_output = f"{frame_count},{TARGET_WIDTH},{TARGET_HEIGHT}\n{b91_string}"
    
    output_filename = f"{video_name}.json"
    with open(output_filename, "w") as f:
        f.write(final_output)
        
    print(f"Generated {output_filename} ({frame_count} frames) -> Delta Lossless Compressed!")

for file in os.listdir('.'):
    if file.endswith('.mp4'):
        process_video(file)
