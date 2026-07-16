from flask import Flask, request, jsonify
import cv2
import os

app = Flask(__name__)

# Track the video handle and the single look-ahead frame
STREAM_STATE = {
    "cap": None,
    "current_file": None,
    "next_frame_idx": -1,
    "next_frame_data": None,
    "total_frames": 0
}

def get_hybrid_frame(filename, cols, rows, target_idx):
    state = STREAM_STATE
    base_dir = os.path.dirname(os.path.abspath(__file__))
    video_path = os.path.join(base_dir, filename)
    if not os.path.exists(video_path):
        video_path = os.path.join(os.getcwd(), filename)
    if not os.path.exists(video_path):
        return None, "File not found"

    # 1. Reset video capture if switching files
    if state["current_file"] != filename or state["cap"] == nil:
        if state["cap"]:
            state["cap"].release()
        cap = cv2.VideoCapture(video_path)
        state["cap"] = cap
        state["current_file"] = filename
        state["total_frames"] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        state["next_frame_idx"] = -1
        state["next_frame_data"] = None

    if state["total_frames"] == 0:
        return None, "Empty video"

    safe_idx = target_idx % state["total_frames"]

    # 2. RAM SWAP HIT: If the requested frame is already waiting in our 1-frame RAM cache
    if safe_idx == state["next_frame_idx"] and state["next_frame_data"] is not None:
        requested_frame = state["next_frame_data"]
    else:
        # Cache miss (Roblox jumped around): Force seek and decode live
        state["cap"].set(cv2.CAP_PROP_POS_FRAMES, safe_idx)
        success, frame = state["cap"].read()
        if not success:
            return None, "Read fail"
        resized = cv2.resize(frame, (cols, rows), interpolation=cv2.INTER_NEAREST)
        requested_frame = resized[:, :, [2, 1, 0]].ravel().tolist()

    # 3. PREFETCH LOOK-AHEAD: Immediately prepare the *next* frame into RAM
    look_ahead_idx = (safe_idx + 1) % state["total_frames"]
    
    # Read the next frame sequentially (blazing fast, no seeking required)
    success, next_frame = state["cap"].read()
    if success:
        resized_next = cv2.resize(next_frame, (cols, rows), interpolation=cv2.INTER_NEAREST)
        state["next_frame_data"] = resized_next[:, :, [2, 1, 0]].ravel().tolist()
        state["next_frame_idx"] = look_ahead_idx
    else:
        # If it fails (e.g. video ended), clear the cache so it forces a reset next request
        state["next_frame_data"] = None
        state["next_frame_idx"] = -1

    return requested_frame, None

@app.route('/', methods=['GET', 'HEAD'])
def home():
    return "Hybrid Look-Ahead Server Online!", 200

@app.route('/get-video-meta', methods=['GET'])
def get_video_meta():
    filename = request.args.get('file', 'OLED_TEST.mp4')
    base_dir = os.path.dirname(os.path.abspath(__file__))
    video_path = os.path.join(base_dir, filename)
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return jsonify({"total_frames": total})

@app.route('/get-frame', methods=['GET'])
def get_frame():
    filename = request.args.get('file', 'OLED_TEST.mp4')
    cols = int(request.args.get('cols', 181))
    rows = int(request.args.get('rows', 102))
    frame_idx = int(request.args.get('frame', 0))

    frame_data, error = get_hybrid_frame(filename, cols, rows, frame_idx)
    if error:
        return jsonify({"error": error}), 400
        
    return jsonify(frame_data)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
