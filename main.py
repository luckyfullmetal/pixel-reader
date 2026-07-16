from flask import Flask, request, jsonify
import cv2
import os
import numpy as np

app = Flask(__name__)
DECODED_VIDEO_CACHE = {}

def get_cached_video(filename, cols, rows):
    cache_key = f"{filename}_{cols}x{rows}"
    if cache_key in DECODED_VIDEO_CACHE:
        return DECODED_VIDEO_CACHE[cache_key]

    video_path = os.path.join(os.getcwd(), filename)
    if not os.path.exists(video_path):
        raise Exception(f"Video file '{filename}' not found.")

    cap = cv2.VideoCapture(video_path)
    frames = []
    
    while True:
        grabbed = cap.grab()
        if not grabbed:
            break
        success, frame = cap.retrieve()
        if not success:
            break
            
        resized_frame = cv2.resize(frame, (cols, rows), interpolation=cv2.INTER_NEAREST)
        rgb_flat = resized_frame[:, :, [2, 1, 0]].ravel().tolist()
        frames.append(rgb_flat)
        
    cap.release()
    DECODED_VIDEO_CACHE[cache_key] = frames
    return frames

@app.route('/', methods=['GET', 'HEAD'])
def home():
    return "Pixel streaming server is online!", 200

# --- NEW EXTRACT META DATA ROUTE ---
@app.route('/get-video-meta', methods=['GET'])
def get_video_meta():
    filename = request.args.get('file', 'video.mp4')
    cols = int(request.args.get('cols', 128))
    rows = int(request.args.get('rows', 72))
    try:
        frames = get_cached_video(filename, cols, rows)
        return jsonify({"total_frames": len(frames)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- NEW SINGLE FRAME STREAM ROUTE ---
@app.route('/get-frame', methods=['GET'])
def get_frame():
    filename = request.args.get('file', 'video.mp4')
    cols = int(request.args.get('cols', 128))
    rows = int(request.args.get('rows', 72))
    frame_idx = int(request.args.get('frame', 0))

    try:
        frames = get_cached_video(filename, cols, rows)
        if frame_idx >= len(frames) or frame_idx < 0:
            frame_idx = 0 # Loop back to start safely
            
        return jsonify(frames[frame_idx])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
