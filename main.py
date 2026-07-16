from flask import Flask, Response
import cv2
import os

app = Flask(__name__)
VIDEOS = {}
COLS, ROWS = 181, 102

def pre_convert_videos():
    curr = os.getcwd()
    for f in os.listdir(curr):
        if f.lower().endswith('.mp4'):
            cap = cv2.VideoCapture(os.path.join(curr, f))
            if not cap.isOpened(): continue
            
            frames = []
            while True:
                success, frame = cap.read()
                if not success: break
                resized = cv2.resize(frame, (COLS, ROWS), interpolation=cv2.INTER_NEAREST)
                frames.append(cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).tobytes())
            
            cap.release()
            VIDEOS[f] = tuple(frames)

pre_convert_videos()

@app.route('/get-frame/<string:filename>/<int:frame_idx>', methods=['GET'])
def get_frame(filename, frame_idx):
    try:
        # Ultra-fast native tuple indexing using the direct route integers
        v_list = VIDEOS[filename]
        return Response(v_list[frame_idx % len(v_list)], mimetype='application/octet-stream')
    except KeyError:
        return "404", 404

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), threaded=True)
