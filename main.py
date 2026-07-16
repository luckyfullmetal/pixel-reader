from flask import Flask, request, jsonify
import cv2
import os

app = Flask(__name__)

STREAM_STATE = {
    "cap": None,
    "current_file": None,
    "total_frames": 0
}

def get_frame_chunk(filename, cols, rows, start_frame, chunk_size=15):
    state = STREAM_STATE
    base_dir = os.path.dirname(os.path.abspath(__file__))
    video_path = os.path.join(base_dir, filename)
    if not os.path.exists(video_path):
        video_path = os.path.join(os.getcwd(), filename)
    if not os.path.exists(video_path):
        return None, "File not found"

    if state["current_file"] != filename or state["cap"] is None:
        if state["cap"]:
            state["cap"].release()
        state["cap"] = cv2.VideoCapture(video_path)
        state["current_file"] = filename
        state["total_frames"] = int(state["cap"].get(cv2.CAP_PROP_FRAME_COUNT))

    if state["total_frames"] == 0:
        return None, "Empty video"

    # Seek to the requested start frame chunk
    safe_start = start_frame % state["total_frames"]
    state["cap"].set(cv2.CAP_PROP_POS_FRAMES, safe_start)

    chunk_data = []
    for _ in range(chunk_size):
        success, frame = state["cap"].read()
        if not success:
            # If video ends mid-chunk, loop back to start
            state["cap"].set(cv2.CAP_PROP_POS_FRAMES, 0)
            success, frame = state["cap"].read()
            if not success: break
            
        resized = cv2.resize(frame, (cols, rows), interpolation=cv2.INTER_NEAREST)
        flat_rgb = resized[:, :, [2, 1, 0]].ravel().tolist()
        chunk_data.append(flat_rgb)

    return chunk_data, None

@app.route('/', methods=['GET', 'HEAD'])
def home():
    return "Chunked Look-Ahead Streaming Active!", 200

@app.route('/get-video-meta', methods=['GET'])
def get_video_meta():
    filename = request.args.get('file', 'OLED_TEST.mp4')
    base_dir = os.path.dirname(os.path.abspath(__file__))
    video_path = os.path.join(base_dir, filename)
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return jsonify({"total_frames": total})

@app.route('/get-chunk', methods=['GET'])
def get_chunk():
    filename = request.args.get('file', 'OLED_TEST.mp4')
    cols = int(request.args.get('cols', 181))
    rows = int(request.args.get('rows', 102))
    start_frame = int(request.args.get('frame', 0))
    size = int(request.args.get('size', 15))

    chunk_data, error = get_frame_chunk(filename, cols, rows, start_frame, size)
    if error:
        return jsonify({"error": error}), 400
        
    return jsonify(chunk_data)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
