from flask import Flask, request, jsonify
import cv2
import os

app = Flask(__name__)

# This holds our "cooked" JSON data matrices in RAM
CONVERTED_VIDEOS = {}

def convert_mp4_to_json(filename, cols, rows):
    """Converts the entire MP4 into pure JSON pixel color digit streams in RAM."""
    video_path = os.path.join(os.getcwd(), filename)
    if not os.path.exists(video_path):
        return None

    cap = cv2.VideoCapture(video_path)
    frames_json = []

    while True:
        success, frame = cap.read()
        if not success:
            break
        
        # 1. Scale frame to match your exact Roblox row/col grid
        resized = cv2.resize(frame, (cols, rows), interpolation=cv2.INTER_NEAREST)
        
        # 2. Extract only the raw color bytes, flip BGR to RGB, and flatten
        flat_rgb_digits = resized[:, :, [2, 1, 0]].ravel().tolist()
        
        # 3. Save this frame's raw color digits
        frames_json.append(flat_rgb_digits)

    cap.release()
    CONVERTED_VIDEOS[filename] = frames_json
    return frames_json

@app.route('/get-frame', methods=['GET'])
def get_frame():
    filename = request.args.get('file', '')
    cols = int(request.args.get('cols', 181))
    rows = int(request.args.get('rows', 102))
    frame_idx = int(request.args.get('frame', 0))

    # If the video isn't converted yet, convert it to JSON right now
    video_matrix = CONVERTED_VIDEOS.get(filename)
    if video_matrix is None:
        video_matrix = convert_mp4_to_json(filename, cols, rows)
        if video_matrix is None:
            return jsonify({"pixels": []}), 404

    # Instantly serve the pure, cooked JSON digits for this frame index
    total_frames = len(video_matrix)
    return jsonify({"pixels": video_matrix[frame_idx % total_frames]})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
