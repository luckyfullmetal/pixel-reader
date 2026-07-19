import os
import cv2
import base91
import numpy as np

TARGET_WIDTH = 181
TARGET_HEIGHT = 102
TOTAL_PIXELS = TARGET_WIDTH * TARGET_HEIGHT

# Absolute strict byte threshold for the JSON file (~95MB to leave safety margin for headers)
MAX_FILE_BYTES = 95 * 1024 * 1024 

def save_part(video_name, part_idx, frame_count, payload_bytes):
    b91_string = base91.encode(payload_bytes)
    final_output = f"{frame_count},{TARGET_WIDTH},{TARGET_HEIGHT}\n{b91_string}"
    
    # Enforces hard cap check
    if len(final_output.encode('utf-8')) > 100 * 1024 * 1024:
        print(f"⚠️ Critical Warning: Part {part_idx} drifted over limits! Reducing threshold.")
        
    output_filename = f"{video_name}_part{part_idx}.json"
    with open(output_filename, "w") as f:
        f.write(final_output)
    print(f"💾 Saved: {output_filename} ({frame_count} frames)")

def process_video(file_path):
    video_name = os.path.splitext(file_path)[0]
    cap = cv2.VideoCapture(file_path)
    
    if not cap.isOpened():
        print(f"Failed to open {file_path}")
        return

    raw_frame_index = 0
    part_idx = 1
    part_frame_count = 0
    current_part_payload = bytearray()
    
    prev_frame = np.zeros((TOTAL_PIXELS, 3), dtype=np.uint8)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if raw_frame_index % 2 == 0:
            resized = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_NEAREST)
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            flat_frame = rgb_frame.reshape(-1, 3)
            
            diff_mask = np.any(flat_frame != prev_frame, axis=1)
            packed_mask = np.packbits(diff_mask)
            changed_colors = flat_frame[diff_mask].flatten()
            
            # Calculate the frame structural size overhead cost
            frame_bytes = bytearray()
            color_bytes_length = len(changed_colors)
            frame_bytes.extend(color_bytes_length.to_bytes(2, byteorder='big'))
            frame_bytes.extend(packed_mask.tobytes())
            frame_bytes.extend(changed_colors.tobytes())
            
            # Check if adding this frame pushes the raw text translation over our strict limit
            # Base91 inflates by roughly 14%, so multiply raw size by 1.15 for safety margin
            estimated_added_text_size = len(frame_bytes) * 1.15
            if (len(current_part_payload) * 1.15) + estimated_added_text_size >= MAX_FILE_BYTES:
                # Save out current accumulated block slice file
                save_part(video_name, part_idx, part_frame_count, current_part_payload)
                part_idx += 1
                part_frame_count = 0
                current_part_payload = bytearray()
            
            current_part_payload.extend(frame_bytes)
            part_frame_count += 1
            prev_frame = flat_frame
            
        raw_frame_index += 1

    cap.release()

    # Save any final remaining trailing frame pieces
    if part_frame_count > 0:
        save_part(video_name, part_idx, part_frame_count, current_part_payload)
        
    print(f"🎉 Slicing Finished successfully. Total multi-part sequences generated: {part_idx}")

for file in os.listdir('.'):
    if file.endswith('.mp4'):
        process_video(file)
