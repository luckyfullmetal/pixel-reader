from flask import Flask, request, Response
import cv2
import os

app = Flask(__name__)

# Compact RAM storage for binary frame arrays
CONVERTED_VIDEOS_BYTES = {}

# Match your exact Roblox grid resolution
COLS, ROWS = 181, 102

def pre_convert_videos():
    """Scans the directory and cooks all MP4s into binary arrays immediately on startup."""
    print("--- STARTING BINARY CONVERSION ---")
    current_dir = os.getcwd()
    
    # Find every MP4 file in your directory
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

        frames_bytes = []
        while True:
            success, frame = cap.read()
            if not success:
                break
            
            # Fast scale down to Roblox grid size
            resized = cv2.resize(frame, (COLS, ROWS), interpolation=cv2.INTER_NEAREST)
            
            # Flip channel order from OpenCV's BGR to RGB, then convert directly to compact bytes
            rgb_frame = resized[:, :, [2, 1, 0]]
            frames_bytes.append(rgb_frame.tobytes())

        cap.release()
        CONVERTED_VIDEOS_BYTES[filename] = frames_bytes
        print(f"[SUCCESS] Cooked '{filename}' ({len(frames_bytes)} frames) into RAM as binary.")
    
    print("--- SERVER READY FOR CONNECTIONS ---")

# Execute conversion instantly on boot
pre_convert_videos()

@app.route('/get-frame', methods=['GET'])
def get_frame():
    filename = request.args.get('file', '')
    frame_idx = int(request.args.get('frame', 0))

    video_bytes_list = CONVERTED_VIDEOS_BYTES.get(filename)
    if not video_bytes_list:
        return "Video Not Found", 404

    # Instant list lookup from RAM
    total_frames = len(video_bytes_list)
    raw_frame_bytes = video_bytes_list[frame_idx % total_frames]

    # Stream the raw bytes directly over the socket without any text wrappers
    return Response(raw_frame_bytes, mimetype='application/octet-stream')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
