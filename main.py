from flask import Flask, request, jsonify
import requests
import cv2
import os
import tempfile

app = Flask(__name__)

# Cache downloaded video files in memory so we only download them ONCE!
VIDEO_CACHE = {}

def get_video_file(video_id):
    """Downloads the Roblox video directly to a local temp file."""
    if video_id in VIDEO_CACHE and os.path.exists(VIDEO_CACHE[video_id]):
        return VIDEO_CACHE[video_id]

    video_url = f"https://assetdelivery.roblox.com/v1/asset/?id={video_id}"
    print(f"Downloading Roblox Video ID: {video_id}...")
    response = requests.get(video_url, stream=True, timeout=30)
    
    if response.status_code != 200:
        raise Exception(f"Failed to download video. HTTP {response.status_code}")

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    for chunk in response.iter_content(chunk_size=1024 * 1024):
        if chunk:
            temp_file.write(chunk)
    temp_file.close()

    VIDEO_CACHE[video_id] = temp_file.name
    return temp_file.name

@app.route('/get-pixels', methods=['GET'])
def get_pixels():
    video_id = request.args.get('id')
    cols = int(request.args.get('cols', 128))
    rows = int(request.args.get('rows', 72))
    frame_num = int(request.args.get('frame', 1))

    if not video_id:
        return jsonify({"error": "Missing video 'id'"}), 400

    try:
        video_path = get_video_file(video_id)
        cap = cv2.VideoCapture(video_path)
        
        # Pull total frame count (might be 0 or -1 on corrupted video metadata)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Fallback loop controller: if metadata is corrupt, we let the frames count upward
        if total_frames <= 0:
            target_frame = frame_num - 1
        else:
            target_frame = (frame_num - 1) % total_frames
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        success, frame = cap.read()
        cap.release()
        
        # If we failed to read (we went past the natural end of the video)
        if not success:
            # Return an empty array. This tells Roblox to reset its counter back to frame 1!
            return jsonify([])

        # Convert colors from OpenCV BGR to standard RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Downscale the frame
        resized_frame = cv2.resize(frame_rgb, (cols, rows), interpolation=cv2.INTER_AREA)
        
        # Pack into pixel coordinate grid
        pixel_grid = []
        for y in range(rows):
            row_pixels = []
            for x in range(cols):
                r, g, b = resized_frame[y, x]
                row_pixels.append([int(r), int(g), int(b)])
            pixel_grid.append(row_pixels)

        return jsonify(pixel_grid)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()
