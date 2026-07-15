from flask import Flask, request, jsonify
import requests
import cv2
import os
import tempfile

app = Flask(__name__)

# Store pre-decoded frame grids in memory: { video_id: [ [grid_frame_1], [grid_frame_2], ... ] }
DECODED_VIDEO_CACHE = {}

def load_and_decode_video(video_id, cols, rows):
    """Downloads the video and decodes all frames sequentially into an in-memory pixel cache."""
    cache_key = f"{video_id}_{cols}x{rows}"
    
    # If already decoded at this resolution, return it!
    if cache_key in DECODED_VIDEO_CACHE:
        return DECODED_VIDEO_CACHE[cache_key]

    # Download Roblox video asset
    video_url = f"https://assetdelivery.roblox.com/v1/asset/?id={video_id}"
    print(f"Downloading and decoding Roblox Video ID: {video_id} at {cols}x{rows}...")
    response = requests.get(video_url, stream=True, timeout=30)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch video. HTTP {response.status_code}")

    # Save binary video data to a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    for chunk in response.iter_content(chunk_size=1024 * 1024):
        if chunk:
            temp_file.write(chunk)
    temp_file.close()

    # Open video with OpenCV
    cap = cv2.VideoCapture(temp_file.name)
    
    frames_list = []
    
    # Read sequentially (this NEVER fails or skips frames!)
    while True:
        success, frame = cap.read()
        if not success:
            break
            
        # Convert BGR (OpenCV default) to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Downscale to the target grid size
        resized_frame = cv2.resize(frame_rgb, (cols, rows), interpolation=cv2.INTER_AREA)
        
        # Format frame as pixel coordinates
        pixel_grid = []
        for y in range(rows):
            row_pixels = []
            for x in range(cols):
                r, g, b = resized_frame[y, x]
                row_pixels.append([int(r), int(g), int(b)])
            pixel_grid.append(row_pixels)
            
        frames_list.append(pixel_grid)
        
    cap.release()
    
    # Clean up the temporary video file from disk
    try:
        os.remove(temp_file.name)
    except OSError:
        pass

    if len(frames_list) == 0:
        raise Exception("No readable frames found in video.")

    # Save to memory cache
    DECODED_VIDEO_CACHE[cache_key] = frames_list
    print(f"Successfully cached {len(frames_list)} frames for Video {video_id}!")
    return frames_list

@app.route('/get-pixels', methods=['GET'])
def get_pixels():
    video_id = request.args.get('id')
    cols = int(request.args.get('cols', 128))
    rows = int(request.args.get('rows', 72))
    frame_num = int(request.args.get('frame', 1))

    if not video_id:
        return jsonify({"error": "Missing video 'id'"}), 400

    try:
        # Load and get cached frames
        cached_frames = load_and_decode_video(video_id, cols, rows)
        
        # Use simple modulo to loop frames forever perfectly
        target_index = (frame_num - 1) % len(cached_frames)
        
        # Pull the exact pixel grid directly from system RAM
        return jsonify(cached_frames[target_index])

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()
