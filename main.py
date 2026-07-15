from flask import Flask, request, jsonify
import requests
import cv2
import os
import tempfile

app = Flask(__name__)

# Retrieve your API key from Render's environment variables
API_KEY = os.environ.get("ROBLOX_API_KEY")

# Store pre-decoded frame grids in memory: { video_id: [ [grid_frame_1], ... ] }
DECODED_VIDEO_CACHE = {}

def load_and_decode_video(video_id, cols, rows):
    """Downloads the authenticated video and decodes all frames sequentially."""
    cache_key = f"{video_id}_{cols}x{rows}"
    
    # If already decoded at this resolution, return it!
    if cache_key in DECODED_VIDEO_CACHE:
        return DECODED_VIDEO_CACHE[cache_key]

    if not API_KEY:
        raise Exception("ROBLOX_API_KEY environment variable is missing on Render!")

    # 1. Fetch the temporary download redirect URL using Roblox's Open Cloud Asset Delivery API
    auth_url = f"https://apis.roblox.com/asset-delivery-api/v1/assetId/{video_id}"
    headers = {
        "x-api-key": API_KEY
    }
    
    print(f"Authenticating with Open Cloud to fetch Video ID: {video_id}...")
    auth_response = requests.get(auth_url, headers=headers, timeout=15)
    
    if auth_response.status_code != 200:
        raise Exception(f"Roblox API authentication failed. HTTP {auth_response.status_code}: {auth_response.text}")

    # Parse the direct download URL from Roblox's response payload
    location_data = auth_response.json()
    download_url = location_data.get("location")
    if not download_url:
        raise Exception("Could not find direct download 'location' in the Roblox API response.")

    # 2. Stream the actual video file binary from the secured location
    print(f"Downloading secured video stream at {cols}x{rows}...")
    response = requests.get(download_url, stream=True, timeout=30)
    if response.status_code != 200:
        raise Exception(f"Failed to stream video binary. HTTP {response.status_code}")

    # Save binary video data to a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    for chunk in response.iter_content(chunk_size=1024 * 1024):
        if chunk:
            temp_file.write(chunk)
    temp_file.close()

    # Open video file with OpenCV
    cap = cv2.VideoCapture(temp_file.name)
    frames_list = []
    
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
    
    # Clean up the temporary file
    try:
        os.remove(temp_file.name)
    except OSError:
        pass

    if len(frames_list) == 0:
        raise Exception("No readable frames found in video file.")

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
        # Fetch or load from memory cache
        cached_frames = load_and_decode_video(video_id, cols, rows)
        
        # Use simple modulo to loop frames forever perfectly
        target_index = (frame_num - 1) % len(cached_frames)
        
        return jsonify(cached_frames[target_index])

    except Exception as e:
        print(f"CRITICAL ERROR on frame fetch: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()
