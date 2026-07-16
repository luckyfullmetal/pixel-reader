from flask import Flask, request, jsonify
import cv2
import os
import requests

app = Flask(__name__)

# CONFIGURATION - Change these to match your GitHub project!
GITHUB_USER = "luckyfullmetal"
GITHUB_REPO = "pixel-reader"
GITHUB_BRANCH = "main" 

@app.route('/get-frame', methods=['GET'])
def get_frame():
    # Grab whatever file name Roblox tells us to look for
    filename = request.args.get('file', '')
    cols = int(request.args.get('cols', 181))
    rows = int(request.args.get('rows', 102))
    frame_idx = int(request.args.get('frame', 0))

    if not filename:
        return jsonify({"error": "No filename provided by Roblox"}), 400

    # Define path where file should live locally on Render
    video_path = os.path.join(os.getcwd(), filename)

    # DYNAMIC GITHUB FETCH: If the file isn't local yet, go pull it from your repo
    if not os.path.exists(video_path):
        github_raw_url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{filename}"
        response = requests.get(github_raw_url, stream=True)
        
        if response.status_code == 200:
            with open(video_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk: f.write(chunk)
        else:
            return jsonify({"error": f"File '{filename}' not found in GitHub repository"}), 404

    # Direct instant frame decoding via OpenCV
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    if total_frames == 0:
        cap.release()
        try: os.remove(video_path) # Clean up corrupted download
        except: pass
        return jsonify({"error": "Invalid or empty video file"}), 400

    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx % total_frames)
    success, frame = cap.read()
    cap.release()

    if not success:
        return jsonify({"error": "Failed to scan frame data"}), 500

    # Hardware scaling execution
    resized = cv2.resize(frame, (cols, rows), interpolation=cv2.INTER_NEAREST)
    pixels = resized[:, :, [2, 1, 0]].ravel().tolist()
    
    return jsonify({
        "total_frames": total_frames,
        "pixels": pixels
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
