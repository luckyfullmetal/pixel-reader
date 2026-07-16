from flask import Flask, request, jsonify
import cv2
import os

app = Flask(__name__)

# Video capture handles and frame caches
VIDEO_HANDLES = {}
PROCESSED_FRAME_CACHE = {}

def get_frame_from_video(filename, cols, rows, frame_idx):
    cache_key = f"{filename}_{cols}x{rows}"
    
    # Initialize cache structure for this video resolution if missing
    if cache_key not in PROCESSED_FRAME_CACHE:
        PROCESSED_FRAME_CACHE[cache_key] = {}
        
    # Super-fast cache hit
    if frame_idx in PROCESSED_FRAME_CACHE[cache_key]:
        return PROCESSED_FRAME_CACHE[cache_key][frame_idx], None

    # Resolve paths reliably on Render/Linux environments
    base_dir = os.path.dirname(os.path.abspath(__file__))
    video_path = os.path.join(base_dir, filename)
    
    # Fallback to current working directory if needed
    if not os.path.exists(video_path):
        video_path = os.path.join(os.getcwd(), filename)

    if not os.path.exists(video_path):
        return None, f"File not found. Tried paths: {video_path}"

    # Open the video handle dynamically if it isn't already open
    if cache_key not in VIDEO_HANDLES:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None, "OpenCV could not open the video file codec container."
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        VIDEO_HANDLES[cache_key] = {"cap": cap, "total_frames": total_frames}

    video_info = VIDEO_HANDLES[cache_key]
    cap = video_info["cap"]
    total_frames = video_info["total_frames"]

    if total_frames == 0:
        return None, "Video contains 0 frames or invalid headers."

    # Loop index safely inside boundary
    safe_frame_idx = frame_idx % total_frames

    # Jump direct to target frame position natively
    cap.set(cv2.CAP_PROP_POS_FRAMES, safe_frame_idx)
    success, frame = cap.read()
    
    if not success:
        # If read fails, try resetting stream pointer to frame 0
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        success, frame = cap.read()
        if not success:
            return None, f"Failed to retrieve frame at position {safe_frame_idx}"

    # Ultra-fast SIMD downsampling
    resized_frame = cv2.resize(frame, (cols, rows), interpolation=cv2.INTER_NEAREST)
    
    # Vectorized conversion directly from BGR to RGB flat array
    rgb_flat = resized_frame[:, :, [2, 1, 0]].ravel().tolist()
    
    # Cache the result so it runs at lightspeed on the next loops
    PROCESSED_FRAME_CACHE[cache_key][safe_frame_idx] = rgb_flat
    
    return rgb_flat, None

@app.route('/', methods=['GET', 'HEAD'])
def home():
    return "Ultra-fast streaming server online!", 200

@app.route('/get-frame', methods=['GET'])
def get_frame():
    filename = request.args.get('file', 'OLED_TEST.mp4')
    cols = int(request.args.get('cols', 181))
    rows = int(request.args.get('rows', 102))
    frame_idx = int(request.args.get('frame', 0))

    frame_data, error_msg = get_frame_from_video(filename, cols, rows, frame_idx)
    
    if error_msg:
        print(f"[ERROR] {error_msg}")  # Spits out clear data into your Render Web Logs
        return jsonify({"error": error_msg}), 404
        
    return jsonify(frame_data)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
