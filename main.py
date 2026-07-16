from flask import Flask, request, jsonify
import cv2
import os

app = Flask(__name__)

@app.route('/get-frame', methods=['GET'])
def get_frame():
    # Grab parameters directly from the Roblox request URL
    filename = request.args.get('file', '')
    cols = int(request.args.get('cols', 181))
    rows = int(request.args.get('rows', 102))
    frame_idx = int(request.args.get('frame', 0))

    # Point directly to the video path
    video_path = os.path.join(os.getcwd(), filename)
    cap = cv2.VideoCapture(video_path)
    
    # Fast-seek directly to the target frame index
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    success, frame = cap.read()
    cap.release()

    if not success:
        return jsonify({"pixels": []}) # Return empty if frame fails

    # FASTEST ENCODER METHOD: Native C++ grid matching
    resized = cv2.resize(frame, (cols, rows), interpolation=cv2.INTER_NEAREST)
    
    # Flatten color data bytes instantly at the machine layer (BGR to RGB)
    pixels = resized[:, :, [2, 1, 0]].ravel().tolist()
    
    return jsonify({"pixels": pixels})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
