from flask import Flask, request, Response, jsonify
import cv2
import os
import json

app = Flask(__name__)

# Cache flattened data directly to save memory
DECODED_VIDEO_CACHE = {}

def load_and_decode_video_flat(filename, cols, rows):
    cache_key = f"{filename}_{cols}x{rows}"
    
    if cache_key in DECODED_VIDEO_CACHE:
        return DECODED_VIDEO_CACHE[cache_key]

    video_path = os.path.join(os.getcwd(), filename)
    
    if not os.path.exists(video_path):
        raise Exception(f"Video file '{filename}' was not found!")

    print(f"Decoding local file: {video_path}...")
    cap = cv2.VideoCapture(video_path)
    
    # We will store frames as a flat list of integers to save massive amounts of RAM
    flat_frames = []
    
    while True:
        success, frame = cap.read()
        if not success:
            break
            
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resized_frame = cv2.resize(frame_rgb, (cols, rows), interpolation=cv2.INTER_AREA)
        
        # Flatten the image array to 1D: [R,G,B, R,G,B, R,G,B...]
        flat_frame = resized_frame.flatten().tolist()
        flat_frames.append(flat_frame)
        
    cap.release()

    if len(flat_frames) == 0:
        raise Exception("No frames decoded from local video file.")

    DECODED_VIDEO_CACHE[cache_key] = flat_frames
    print(f"Successfully cached {len(flat_frames)} flat frames locally!")
    return flat_frames

@app.route('/get-all-pixels', methods=['GET'])
def get_all_pixels():
    filename = request.args.get('file', 'video.mp4')
    cols = int(request.args.get('cols', 128))
    rows = int(request.args.get('rows', 72))

    try:
        all_frames = load_and_decode_video_flat(filename, cols, rows)
        
        # Stream the JSON in chunks to prevent memory spikes
        def generate():
            yield "["
            for i, frame in enumerate(all_frames):
                if i > 0:
                    yield ","
                yield json.dumps(frame)
            yield "]"
            
        return Response(generate(), mimetype='application/json')
        
    except Exception as e:
        print(f"CRITICAL ERROR on video load: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()
