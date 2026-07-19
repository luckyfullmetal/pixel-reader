import os
import cv2
import base91
import numpy as np

TARGET_WIDTH = 181
TARGET_HEIGHT = 102
TOTAL_PIXELS = TARGET_WIDTH * TARGET_HEIGHT
FRAMES_PER_PART = 512  # Fixed frame-based target threshold

print("⚙️ Video Matrix Encoder initialized (512-frame chunk mode).")

# PHASE 0: Clean target directory
print("🧹 Cleaning directory... Removing old .json files.")
deleted_count = 0
for file in os.listdir('.'):
    if file.endswith('.json'):
        try:
            os.remove(file)
            deleted_count += 1
        except Exception as e:
            print(f"⚠️ Could not delete {file}: {e}")

if deleted_count > 0:
    print(f"🗑️ Successfully removed {deleted_count} old JSON file(s).")
else:
    print("✨ Directory is already clean.")

def save_part(video_name, part_idx, frame_count, payload_bytes):
    b91_string = base91.encode(payload_bytes)
    final_output = f"{frame_count},{TARGET_WIDTH},{TARGET_HEIGHT}\n{b91_string}"
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
    force_keyframe = True 

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if raw_frame_index % 2 == 0:
            resized = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_NEAREST)
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            flat_frame = rgb_frame.reshape(-1, 3)
            
            # Check if this frame marks a new slice file boundary
            if part_frame_count >= FRAMES_PER_PART:
                save_part(video_name, part_idx, part_frame_count, current_part_payload)
                part_idx += 1
                part_frame_count = 0
                current_part_payload = bytearray()
                force_keyframe = True  # Next chunk MUST start with a full layout update
            
            if force_keyframe:
                diff_mask = np.ones(TOTAL_PIXELS, dtype=bool)
                force_keyframe = False
            else:
                diff_mask = np.any(flat_frame != prev_frame, axis=1)

            packed_mask = np.packbits(diff_mask)
            changed_colors = flat_frame[diff_mask].flatten()
            
            frame_bytes = bytearray()
            color_bytes_length = len(changed_colors)
            frame_bytes.extend(color_bytes_length.to_bytes(2, byteorder='big'))
            frame_bytes.extend(packed_mask.tobytes())
            frame_bytes.extend(changed_colors.tobytes())
            
            current_part_payload.extend(frame_bytes)
            part_frame_count += 1
            prev_frame = flat_frame
            
        raw_frame_index += 1

    cap.release()

    if part_frame_count > 0:
        save_part(video_name, part_idx, part_frame_count, current_part_payload)
        
    print(f"🎉 Slicing Finished. Total multi-part sequences generated: {part_idx}")

for file in os.listdir('.'):
    if file.endswith('.mp4'):
        process_video(file)
