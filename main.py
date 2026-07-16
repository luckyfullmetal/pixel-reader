from flask import Flask, request, jsonify
import cv2
import os
import numpy as np
import gc

app = Flask(__name__)

# Highly compressed raw binary RAM cache
GLOBAL_FRAME_CACHE = None
TOTAL_FRAMES = 0

def pre_decode_video_lean(filename="OLED_TEST.mp4", cols=181, rows=102):
    global GLOBAL_FRAME_CACHE, TOTAL_FRAMES
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    video_path = os.path.join(base_dir, filename)
    if not os.path.exists(video_path):
        video_path = os.path.join(os.getcwd(), filename)
    if not os.path.exists(video_path):
        print(f"[ERROR] Video file {filename} not found.")
        return

    cap = cv2.VideoCapture(video_path)
    temp_frames = []
    
    print("[SERVER] Starting ultra-low memory pre-decode...")
    while True:
        success, frame = cap.read()
        if not success:
            break
        
        resized = cv2.resize(frame, (cols, rows), interpolation=cv2.INTER_NEAREST)
        # Convert directly to uint8 array (1 byte per pixel color value instead of 28-byte Python objects)
        rgb_flat = resized[:, :, [2, 1, 0]].ravel()
        temp_frames.append(rgb_flat)
        
    cap.release()
    
    if len(temp_frames) > 0:
        TOTAL_FRAMES = len(temp_frames)
        # Stack all frames into a single continuous block of C-memory (extremely RAM-friendly)
        GLOBAL_FRAME_CACHE = np.vstack(temp_frames).astype(np.uint8)
        print(f"[SERVER] Cached {TOTAL_FRAMES} frames successfully using just {GLOBAL_FRAME_CACHE.nbytes / (1024 * 1024):.2f} MB of RAM!")
    else:
        print("[ERROR] No frames could be decoded.")
        
    # Free temporary loading structures
    del temp_frames
    gc.collect()

# Run the compact loader
pre_decode_video_lean()

@app.route('/', methods=['GET', 'HEAD'])
def home():
    return "RAM-Cached Low-Memory Streaming Server Online!", 200

@app.route('/get-video-meta', methods=['GET'])
def get_video_meta():
    return jsonify({"total_frames": TOTAL_FRAMES})

@app.route('/get-frame', methods=['GET'])
def get_frame():
    frame_idx = int(request.args.get('frame', 0))
    if TOTAL_FRAMES == 0 or GLOBAL_FRAME_CACHE is None:
        return jsonify([]), 404
        
    safe_idx = frame_idx % TOTAL_FRAMES
    # Extract the requested frame's row from the continuous memory block and convert to standard JSON list
    return jsonify(GLOBAL_FRAME_CACHE[safe_idx].tolist())

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
