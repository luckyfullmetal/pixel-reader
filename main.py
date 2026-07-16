from flask import Flask, request, jsonify
import cv2
import os

app = Flask(__name__)

@app.route('/get-frame', methods=['GET'])
def get_frame():
    filename = request.args.get('file', 'OLED_TEST.mp4')
    cols = int(request.args.get('cols', 181))
    rows = int(request.args.get('rows', 102))
    frame_idx = int(request.args.get('frame', 0))

    # Build file paths safely
    base_dir = os.path.dirname(os.path.abspath(__file__))
    video_path = os.path.join(base_dir, filename)
    if not os.path.exists(video_path):
        video_path = os.path.join(os.getcwd(), filename)

    # Open video file instantly on-demand
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    if total_frames == 0:
        cap.release()
        return jsonify({"error": "Video not found"}), 400

    # Fast seek directly to requested index
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx % total_frames)
    success, frame = cap.read()
    cap.release()

    if not success:
        return jsonify({"error": "Failed to read frame"}), 500

    # Blazing fast C++ hardware scaling matching your Roblox row/col grid
    resized = cv2.resize(frame, (cols, rows), interpolation=cv2.INTER_NEAREST)
    
    # Ultra-fast color-flip and array flattening (BGR -> RGB)
    pixels = resized[:, :, [2, 1, 0]].ravel().tolist()
    
    return jsonify({
        "total_frames": total_frames,
        "pixels": pixels
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
