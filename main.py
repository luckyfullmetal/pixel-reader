from flask import Flask, request, jsonify
import requests
import cv2
import os
import tempfile

app = Flask(__name__)

# Memory cache: { "imgur_url_cols_rows": [ [grid_frame_1], ... ] }
DECODED_VIDEO_CACHE = {}

def load_and_decode_video(video_url, cols, rows):
    cache_key = f"{video_url}_{cols}x{rows}"
    
    # If this video is already cached, return it instantly!
    if cache_key in DECODED_VIDEO_CACHE:
        return DECODED_VIDEO_CACHE[cache_key]

    print(f"Downloading direct video stream from: {video_url}...")
    response = requests.get(video_url, stream=True, timeout=30)
    
    if response.status_code != 200:
        raise Exception(f"Failed to download video from Imgur. HTTP {response.status_code}")

    # Use a secure local temp path with no digits in the file name to avoid OpenCV bugs
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, "temp_render_file.mp4")

    # Save video binary completely to disk
    with open(temp_file_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
                f.flush()

    # Decode frames using OpenCV
    print("Decoding frames with OpenCV...")
    cap = cv2.VideoCapture(temp_file_path)
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
    
    # Clean up temp file
    try:
        os.remove(temp_file_path)
    except OSError:
        pass

    if len(frames_list) == 0:
        raise Exception("No readable frames found in video file. Ensure your Imgur URL is a direct .mp4 file!")

    DECODED_VIDEO_CACHE[cache_key] = frames_list
    print(f"Successfully cached {len(frames_list)} frames!")
    return frames_list

@app.route('/get-pixels', methods=['GET'])
def get_pixels():
    # We now accept a direct 'url' parameter instead of 'id'
    video_url = request.args.get('url')
    cols = int(request.args.get('cols', 128))
    rows = int(request.args.get('rows', 72))
    frame_num = int(request.args.get('frame', 1))

    if not video_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    try:
        cached_frames = load_and_decode_video(video_url, cols, rows)
        target_index = (frame_num - 1) % len(cached_frames)
        return jsonify(cached_frames[target_index])

    except Exception as e:
        print(f"CRITICAL ERROR on frame fetch: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()
