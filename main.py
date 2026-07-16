from flask import Flask, request, jsonify
import cv2
import os

app = Flask(__name__)

# This will store the entirely decoded video in memory
GLOBAL_FRAME_CACHE = []
TOTAL_FRAMES = 0

def pre_decode_video(filename="OLED_TEST.mp4", cols=181, rows=102):
    global GLOBAL_FRAME_CACHE, TOTAL_FRAMES
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    video_path = os.path.join(base_dir, filename)
    if not os.path.exists(video_path):
        video_path = os.path.join(os.getcwd(), filename)
    if not os.path.exists(video_path):
        print(f"[ERROR] Video file {filename} not found.")
        return

    cap = cv2.VideoCapture(video_path)
    frames = []
    
    print("[SERVER] Starting full video pre-decode into RAM...")
    while True:
        success, frame = cap.read()
        if not success:
            break
        # Fast resize and flatten directly to list
        resized = cv2.resize(frame, (cols, rows), interpolation=cv2.INTER_NEAREST)
        rgb_flat = resized[:, :, [2, 1, 0]].ravel().tolist()
        frames.append(rgb_flat)
        
    cap.release()
    GLOBAL_FRAME_CACHE = frames
    TOTAL_FRAMES = len(frames)
    print(f"[SERVER] Successfully cached {TOTAL_FRAMES} frames in memory!")

# Pre-load on startup
pre_decode_video()

@app.route('/', methods=['GET', 'HEAD'])
def home():
    return "RAM-Cached Streaming Server Online!", 200

@app.route('/get-video-meta', methods=['GET'])
def get_video_meta():
    return jsonify({"total_frames": TOTAL_FRAMES})

@app.route('/get-frame', methods=['GET'])
def get_frame():
    frame_idx = int(request.args.get('frame', 0))
    if TOTAL_FRAMES == 0:
        return jsonify([]), 404
        
    safe_idx = frame_idx % TOTAL_FRAMES
    return jsonify(GLOBAL_FRAME_CACHE[safe_idx])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
