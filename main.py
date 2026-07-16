from flask import Flask, request, jsonify
import cv2
import os

app = Flask(__name__)

# This will hold compact byte arrays instead of bloated lists
CONVERTED_VIDEOS_BYTES = {}

# Match your exact Roblox grid resolution
COLS, ROWS = 181, 102

def pre_convert_videos():
    """Scans directory and cooks MP4s into compact bytes arrays on startup."""
    print("--- STARTING ULTRA-LOW MEMORY CONVERSION ---")
    current_dir = os.getcwd()
    
    mp4_files = [f for f in os.listdir(current_dir) if f.lower().endswith('.mp4')]
    
    if not mp4_files:
        print("[WARNING] No .mp4 files found!")
        return

    for filename in mp4_files:
        video_path = os.path.join(current_dir, filename)
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            print(f"[ERROR] Could not open {filename}")
            continue

        frames_bytes = []
        while True:
            success, frame = cap.read()
            if not success:
                break
            
            # Fast scale down to Roblox grid size
            resized = cv2.resize(frame, (COLS, ROWS), interpolation=cv2.INTER_NEAREST)
            # Flip BGR to RGB
            rgb_frame = resized[:, :, [2, 1, 0]]
            
            # Convert directly to a compact C-level byte string (Zero overhead!)
            frames_bytes.append(rgb_frame.tobytes())

        cap.release()
        CONVERTED_VIDEOS_BYTES[filename] = frames_bytes
        print(f"[SUCCESS] Cooked '{filename}' safely into RAM using ultra-low memory!")
    
    print("--- READY FOR ROBLOX CONNECTIONS ---")

# Pre-cook immediately when Render boots
pre_convert_videos()

@app.route('/get-frame', methods=['GET'])
def get_frame():
    filename = request.args.get('file', '')
    frame_idx = int(request.args.get('frame', 0))

    video_bytes_list = CONVERTED_VIDEOS_BYTES.get(filename)
    if not video_bytes_list:
        return jsonify({"pixels": [], "error": "Video not found"}), 404

    total_frames = len(video_bytes_list)
    raw_frame_bytes = video_bytes_list[frame_idx % total_frames]

    # Only convert the single requested frame into a JSON list right before sending it
    pixel_digits = list(raw_frame_bytes)

    return jsonify({"pixels": pixel_digits})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
