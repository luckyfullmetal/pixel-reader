from flask import Flask, request, jsonify
import cv2
import os

app = Flask(__name__)

# Memory cache for our pre-processed frames
DECODED_VIDEO_CACHE = {}

def load_and_decode_video(filename, cols, rows):
    cache_key = f"{filename}_{cols}x{rows}"
    
    if cache_key in DECODED_VIDEO_CACHE:
        return DECODED_VIDEO_CACHE[cache_key]

    # Look for the video file right in our repository folder!
    video_path = os.path.join(os.getcwd(), filename)
    
    if not os.path.exists(video_path):
        raise Exception(f"Video file '{filename}' was not found in the root directory!")

    print(f"Decoding local file: {video_path} at {cols}x{rows}...")
    cap = cv2.VideoCapture(video_path)
    frames_list = []
    
    while True:
        success, frame = cap.read()
        if not success:
            break
            
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resized_frame = cv2.resize(frame_rgb, (cols, rows), interpolation=cv2.INTER_AREA)
        
        pixel_grid = []
        for y in range(rows):
            row_pixels = []
            for x in range(cols):
                r, g, b = resized_frame[y, x]
                row_pixels.append([int(r), int(g), int(b)])
            pixel_grid.append(row_pixels)
            
        frames_list.append(pixel_grid)
        
    cap.release()

    if len(frames_list) == 0:
        raise Exception("Failed to read any frames from the local video file. It might be corrupted.")

    DECODED_VIDEO_CACHE[cache_key] = frames_list
    print(f"Successfully cached {len(frames_list)} frames locally!")
    return frames_list

@app.route('/get-all-pixels', methods=['GET'])
def get_all_pixels():
    # We now look for a local filename (defaults to video.mp4)
    filename = request.args.get('file', 'video.mp4')
    cols = int(request.args.get('cols', 128))
    rows = int(request.args.get('rows', 72))

    try:
        all_frames = load_and_decode_video(filename, cols, rows)
        return jsonify(all_frames)
    except Exception as e:
        print(f"CRITICAL ERROR on video load: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()
