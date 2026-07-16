from flask import Flask, request, jsonify
import cv2
import os

app = Flask(__name__)

# Track active video readers to keep streaming fast
ACTIVE_READERS = {}

def get_stream_frame(filename, cols, rows, frame_idx):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    video_path = os.path.join(base_dir, filename)
    if not os.path.exists(video_path):
        video_path = os.path.join(os.getcwd(), filename)
    if not os.path.exists(video_path):
        return None, f"File {filename} not found."

    # Init or reuse the open file handle
    if filename not in ACTIVE_READERS:
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        ACTIVE_READERS[filename] = {"cap": cap, "last_idx": -1, "total": total_frames}
    
    reader = ACTIVE_READERS[filename]
    cap = reader["cap"]
    total_frames = reader["total"]

    if total_frames == 0:
        return None, "Empty video file."

    safe_idx = frame_idx % total_frames

    # SPEED TRICK: If Roblox wants the next frame sequentially, just read it.
    # Otherwise, perform a heavy seek jump.
    if safe_idx != reader["last_idx"] + 1:
        cap.set(cv2.CAP_PROP_POS_FRAMES, safe_idx)
    
    success, frame = cap.read()
    
    # If the handle got stale or failed, reset and try once more
    if not success:
        cap.release()
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, safe_idx)
        success, frame = cap.read()
        ACTIVE_READERS[filename]["cap"] = cap

    if not success:
        return None, "Failed to read frame."

    # Update sequence tracker
    reader["last_idx"] = safe_idx

    # Downsample and flatten instantly
    resized = cv2.resize(frame, (cols, rows), interpolation=cv2.INTER_NEAREST)
    return resized[:, :, [2, 1, 0]].ravel().tolist(), None

@app.route('/', methods=['GET', 'HEAD'])
def home():
    return "Streaming direct from disk!", 200

@app.route('/get-video-meta', methods=['GET'])
def get_video_meta():
    filename = request.args.get('file', 'OLED_TEST.mp4')
    base_dir = os.path.dirname(os.path.abspath(__file__))
    video_path = os.path.join(base_dir, filename)
    
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    
    return jsonify({"total_frames": total_frames})

@app.route('/get-frame', methods=['GET'])
def get_frame():
    filename = request.args.get('file', 'OLED_TEST.mp4')
    cols = int(request.args.get('cols', 181))
    rows = int(request.args.get('rows', 102))
    frame_idx = int(request.args.get('frame', 0))

    frame_data, error = get_stream_frame(filename, cols, rows, frame_idx)
    if error:
        return jsonify({"error": error}), 400
        
    return jsonify(frame_data)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
