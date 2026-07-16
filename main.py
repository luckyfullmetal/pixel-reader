from flask import Flask, request, jsonify
import cv2
import os

app = Flask(__name__)

# This dictionary holds our raw video digit matrices directly in RAM
RAM_VIDEO_CACHE = {}

def load_video_to_ram(filename, cols, rows):
    """
    Reads the MP4 and instantly compiles it into a pure 
    matrix of digit lists directly inside Python's RAM.
    """
    video_path = os.path.join(os.getcwd(), filename)
    if not os.path.exists(video_path):
        return None

    cap = cv2.VideoCapture(video_path)
    compiled_matrix = []

    while True:
        success, frame = cap.read()
        if not success:
            break
        
        # Blazing fast C++ hardware scaling matching your Roblox row/col grid
        resized = cv2.resize(frame, (cols, rows), interpolation=cv2.INTER_NEAREST)
        
        # Ultra-fast color-flip and array flattening (BGR -> RGB) into pure digits
        flat_rgb = resized[:, :, [2, 1, 0]].ravel().tolist()
        compiled_matrix.append(flat_rgb)

    cap.release()
    
    # Save the compiled raw data array into RAM cache
    RAM_VIDEO_CACHE[filename] = compiled_matrix
    return compiled_matrix

@app.route('/get-frame', methods=['GET'])
def get_frame():
    filename = request.args.get('file', '')
    cols = int(request.args.get('cols', 181))
    rows = int(request.args.get('rows', 102))
    frame_idx = int(request.args.get('frame', 0))

    if not filename:
        return jsonify({"pixels": [], "error": "No filename provided"}), 400

    # Look up the video data from RAM cache
    matrix = RAM_VIDEO_CACHE.get(filename)
    
    # If it's not in RAM yet, compile it right now on the fly
    if matrix is None:
        matrix = load_video_to_ram(filename, cols, rows)
        if matrix is None:
            return jsonify({"pixels": [], "error": f"File '{filename}' not found on server"}), 404

    # Instant array lookup from RAM (Pure math, zero image decoding overhead)
    total_frames = len(matrix)
    pixels = matrix[frame_idx % total_frames]

    return jsonify({"pixels": pixels})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
