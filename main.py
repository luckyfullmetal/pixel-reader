from flask import Flask, request, Response
import cv2
import os

app = Flask(__name__)

# Compact RAM storage for pre-baked, zero-processing 1D byte arrays
CONVERTED_VIDEOS_BYTES = {}

# Target resolution matching your Roblox grid
COLS, ROWS = 181, 102

def pre_convert_videos():
    """Cooks all MP4 frames directly into 1D, pre-formatted network byte arrays on startup."""
    print("--- STARTING 1D ULTRA-CONVERSION ---")
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
            
            # 1. Hardware-level matrix scaling
            resized = cv2.resize(frame, (COLS, ROWS), interpolation=cv2.INTER_NEAREST)
            
            # 2. Extract channels directly on startup to remove runtime layout overhead
            # Swaps BGR -> RGB layout permanently in RAM
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            
            # 3. Flatten the image matrix completely into a raw, one-dimensional byte string
            frames_bytes.append(rgb_frame.tobytes())

        cap.release()
        
        # Lock into memory as a flat tuple for slightly faster lookup speed than a list
        CONVERTED_VIDEOS_BYTES[filename] = tuple(frames_bytes)
        print(f"[SUCCESS] Cooked '{filename}' ({len(frames_bytes)} frames) into 1D RAM arrays.")
    
    print("--- SERVER READY: ZERO RUNTIME OVERHEAD METRIC ACTIVE ---")

# Pre-bake everything on boot
pre_convert_videos()

@app.route('/get-frame', methods=['GET'])
def get_frame():
    # Instantaneous string lookup from route arguments
    filename = request.args.get('file', '')
    
    video_bytes_list = CONVERTED_VIDEOS_BYTES.get(filename)
    if not video_bytes_list:
        return "Video Not Found", 404

    # Direct 1D index slicing from a pre-allocated tuple in memory
    # Modulo handling allows video loops with practically zero latency
    raw_frame_bytes = video_bytes_list[int(request.args.get('frame', 0)) % len(video_bytes_list)]

    # Stream the raw bytes directly over the socket without wrappers or encoding translations
    return Response(raw_frame_bytes, mimetype='application/octet-stream')

if __name__ == '__main__':
    # Threaded mode allows concurrent downloads without blocking the loop worker thread
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), threaded=True)
