from flask import Flask, request, Response, jsonify
import cv2
import os
import json
import numpy as np

app = Flask(__name__)
DECODED_VIDEO_CACHE = {}

def load_and_decode_video_flat(filename, cols, rows):
    cache_key = f"{filename}_{cols}x{rows}"
    if cache_key in DECODED_VIDEO_CACHE:
        return DECODED_VIDEO_CACHE[cache_key]

    video_path = os.path.join(os.getcwd(), filename)
    if not os.path.exists(video_path):
        raise Exception("Video file not found")

    cap = cv2.VideoCapture(video_path)
    flat_frames = []
    
    # We use cv2's grab/retrieve pipeline which bypasses some CPU overhead
    while True:
        grabbed = cap.grab()
        if not grabbed:
            break
            
        success, frame = cap.retrieve()
        if not success:
            break
            
        # 1. Faster color conversion & resizing using native SIMD (INTER_NEAREST is up to 5x faster)
        resized_frame = cv2.resize(frame, (cols, rows), interpolation=cv2.INTER_NEAREST)
        
        # 2. Swap BGR to RGB and flatten at native hardware speed using advanced NumPy indexing
        rgb_flat = resized_frame[:, :, [2, 1, 0]].ravel().tolist()
        flat_frames.append(rgb_flat)
        
    cap.release()
    DECODED_VIDEO_CACHE[cache_key] = flat_frames
    return flat_frames

@app.route('/get-all-pixels', methods=['GET'])
def get_all_pixels():
    filename = request.args.get('file', 'video.mp4')
    cols = int(request.args.get('cols', 128))
    rows = int(request.args.get('rows', 72))

    try:
        all_frames = load_and_decode_video_flat(filename, cols, rows)
        
        # Optimized chunk generator: dumps arrays with minimal Python string building overhead
        def generate():
            yield "["
            for i, frame in enumerate(all_frames):
                if i > 0:
                    yield ","
                yield json.dumps(frame)
            yield "]"
            
        return Response(generate(), mimetype='application/json')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()
