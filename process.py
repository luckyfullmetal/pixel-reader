import os
import cv2
import base91
import numpy as np

TARGET_WIDTH = 181
TARGET_HEIGHT = 102
TOTAL_PIXELS = TARGET_WIDTH * TARGET_HEIGHT

def process_video(file_path):
    video_name = os.path.splitext(file_path)[0]
    cap = cv2.VideoCapture(file_path)
    
    if not cap.isOpened():
        print(f"Failed to open {file_path}")
        return

    frame_count = 0
    raw_frame_index = 0
    compressed_payload = bytearray()
    
    prev_frame = np.zeros((TOTAL_PIXELS, 3), dtype=np.uint8)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if raw_frame_index % 2 == 0:
            resized = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_NEAREST)
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            flat_frame = rgb_frame.reshape(-1, 3)
            
            # Create a true boolean array of what changed
            diff_mask = np.any(flat_frame != prev_frame, axis=1)
            
            # Pack the boolean mask array directly into raw bits (8 pixels per byte)
            packed_mask = np.packbits(diff_mask)
            
            # Collect the raw RGB color bytes only for pixels that actually changed
            changed_colors = flat_frame[diff_mask].flatten()
            
            # Write out: 2 bytes for the size of the color payload + the bitmask + the colors
            color_bytes_length = len(changed_colors)
            compressed_payload.extend(color_bytes_length.to_bytes(2, byteorder='big'))
            compressed_payload.extend(packed_mask.tobytes())
            compressed_payload.extend(changed_colors.tobytes())

            prev_frame = flat_frame
            frame_count += 1
        raw_frame_index += 1

    cap.release()

    b91_string = base91.encode(compressed_payload)
    final_output = f"{frame_count},{TARGET_WIDTH},{TARGET_HEIGHT}\n{b91_string}"
    
    output_filename = f"{video_name}.json"
    with open(output_filename, "w") as f:
        f.write(final_output)
        
    print(f"📉 Bare-Metal Squeeze Complete -> {output_filename} is at the absolute floor size!")

for file in os.listdir('.'):
    if file.endswith('.mp4'):
        process_video(file)
