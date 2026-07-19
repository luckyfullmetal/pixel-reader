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
    
    prev_frame = [[0, 0, 0]] * (TARGET_WIDTH * TARGET_HEIGHT)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if raw_frame_index % 2 == 0:
            resized = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_NEAREST)
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            flat_frame = rgb_frame.reshape(-1, 3)
            
            # Find all pixel modifications for this frame
            changed_pixels = []
            for idx, pixel in enumerate(flat_frame):
                prev_pixel = prev_frame[idx]
                if pixel[0] != prev_pixel[0] or pixel[1] != prev_pixel[1] or pixel[2] != prev_pixel[2]:
                    changed_pixels.append((idx, pixel))
            
            # Compress the changes using coordinate runs
            diff_bytes = bytearray()
            i = 0
            while i < len(changed_pixels):
                start_idx, color = changed_pixels[i]
                run_length = 1
                
                # Check how many consecutive pixels are also changing in a row
                while (i + run_length < len(changed_pixels) and 
                       changed_pixels[i + run_length][0] == start_idx + run_length and 
                       run_length < 255):
                    run_length += 1
                
                # Write: Start Index (2 bytes) + Run Length (1 byte)
                diff_bytes.extend(start_idx.to_bytes(2, byteorder='big'))
                diff_bytes.append(run_length)
                
                # Write the raw RGB colors for this run consecutive sequence
                for k in range(run_length):
                    run_color = changed_pixels[i + k][1]
                    diff_bytes.extend([run_color[0], run_color[1], run_color[2]])
                
                i += run_length
            
            # Number of structural instruction blocks in this frame
            num_blocks = len(diff_bytes) # We track the exact byte chunk length
            compressed_payload.extend(num_blocks.to_bytes(2, byteorder='big'))
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
        
    print(f"🎉 Generated {output_filename} ({frame_count} frames) -> Lossless RLE Coordinates!")

for file in os.listdir('.'):
    if file.endswith('.mp4'):
        process_video(file)
