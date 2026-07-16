from flask import Flask, request, jsonify
import cv2
import os

app = Flask(__name__)

# Direct RAM storage for cooked pixel data
CONVERTED_VIDEOS = {}

# Match your exact Roblox grid resolution
COLS, ROWS = 181, 102

def pre_convert_videos():
    """Scans the directory and cooks all MP4s into RAM immediately on startup."""
    print("--- STARTING AUTO-CONVERSION ---")
    current_dir = os.getcwd()
    
    # Find every MP4 file in your repository
    mp4_files = [f for f in os.listdir(current_dir) if f.lower().endswith('.mp4')]
    
    if not mp4_files:
        print("[WARNING] No .mp4 files found in the directory!")
        return

    for filename in mp4_files:
        video_path = os.path.join(current_dir, filename)
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            print(f"[ERROR] Could not open {filename}")
            continue

        frames_json = []
        while True:
            success, frame = cap.read()
            if not success:
                break
            
            # Fast scale down to Roblox grid size
            resized = cv2.resize(frame, (COLS, ROWS), interpolation=cv2.INTER_NEAREST)
            # Extract raw color values (BGR -> RGB) and flatten
            flat_rgb = resized[:, :, [2, 1, 0]].ravel().tolist()
            frames_json.append(flat_rgb)

        cap.release()
        CONVERTED_VIDEOS[filename] = frames_json
        print(f"[SUCCESS] Cooked '{filename}' ({len(frames_json)} frames) into RAM!")
    
    print("--- READY FOR ROBLOX CONNECTIONS ---")

# Trigger the conversion instantly when Render runs the file
pre_convert_videos()

@app.route('/get-frame', methods=['GET'])
def get_frame():
    filename = request.args.get('file', '')
    frame_idx = int(request.args.get('frame', 0))

    video_matrix = CONVERTED_VIDEOS.get(filename)
    if not video_matrix:
        return jsonify({
            "pixels": [], 
            "error": f"Video '{filename}' not pre-loaded. Checked files: {list(CONVERTED_VIDEOS.keys())}"
        }), 404

    # Direct, instant list lookup from RAM
    total_frames = len(video_matrix)
    return jsonify({"pixels": video_matrix[frame_idx % total_frames]})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
