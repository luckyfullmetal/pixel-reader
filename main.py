from flask import Flask, request, jsonify
from PIL import Image
import requests
import io

app = Flask(__name__)

@app.route('/get-pixels', methods=['GET'])
def get_pixels():
    image_url = request.args.get('url')
    asset_id = request.args.get('id')
    cols = int(request.args.get('cols', 64))
    rows = int(request.args.get('rows', 36))
    
    if not image_url and not asset_id:
        return jsonify({"error": "Missing 'url' or 'id'"}), 400

    try:
        # Determine target URL (Use raw URL, or pull from Roblox delivery service)
        target_url = image_url if image_url else f"https://assetdelivery.roblox.com/v1/asset/?id={asset_id}"
        
        # Download and read the image
        response = requests.get(target_url, timeout=10)
        img = Image.open(io.BytesIO(response.content)).convert('RGBA')
        
        # Downscale directly to your grid size using high-quality sampling
        img = img.resize((cols, rows), Image.Resampling.LANCZOS)
        
        # Structure pixel data as a simplified grid: list of rows [ [R, G, B], ... ]
        pixel_grid = []
        for y in range(rows):
            row_pixels = []
            for x in range(cols):
                r, g, b, a = img.getpixel((x, y))
                # If transparent, return black (0, 0, 0)
                if a <= 15:
                    row_pixels.append([0, 0, 0])
                else:
                    row_pixels.append([r, g, b])
            pixel_grid.append(row_pixels)
            
        return jsonify(pixel_grid)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
