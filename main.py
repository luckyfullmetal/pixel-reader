from flask import Flask, request, Response, jsonify
import cv2
import os
import json

app = Flask(__name__)
DECODED_VIDEO_CACHE = {}

def load_and_decode_video_flat(filename, cols, rows):
    cache_key = f"{filename}_{cols}x{rows}"
    if cache_key in DECODED_VIDEO_CACHE:
        return DECODED_VIDEO_CACHE[cache_key]

    video_path = os.path.join(os.getcwd(), filename)
    if not os.path.exists(video_path):
        raise Exception(f"Video file '{filename}' was not found!")

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = 12.0

    flat_frames = []
    while True:
        success, frame = cap.read()
        if not success:
            break
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resized_frame = cv2.resize(frame_rgb, (cols, rows), interpolation=cv2.INTER_AREA)
        flat_frames.append(resized_frame.flatten().tolist())
        
    cap.release()

    if len(flat_frames) == 0:
        raise Exception("No frames decoded from local video file.")

    video_data = {"fps": fps, "frames": flat_frames}
    DECODED_VIDEO_CACHE[cache_key] = video_data
    return video_data

@app.route('/get-all-pixels', methods=['GET'])
def get_all_pixels():
    filename = request.args.get('file', 'video.mp4')
    cols = int(request.args.get('cols', 128))
    rows = int(request.args.get('rows', 72))

    try:
        video_data = load_and_decode_video_flat(filename, cols, rows)
        
        def generate():
            yield f'{{"fps": {video_data["fps"]}, "frames": ['
            for i, frame in enumerate(video_data["frames"]):
                if i > 0:
                    yield ","
                yield json.dumps(frame)
            yield "]}}"
            
        return Response(generate(), mimetype='application/json')
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()
