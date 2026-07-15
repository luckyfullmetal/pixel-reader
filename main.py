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
        # If an asset_id is provided, resolve it to a direct PNG image link using Roblox's Thumbnails API
        if asset_id:
            thumb_api = f"https://thumbnails.roblox.com/v1/assets?assetIds={asset_id}&size=150x150&format=Png"
            thumb_res = requests.get(thumb_api, timeout=10).json()
            
            if "data" in thumb_res and len(thumb_res["data"]) > 0:
                target_url = thumb_res["data"][0]["imageUrl"]
            else:
                return jsonify({"error": "Failed to resolve Roblox asset thumbnail"}), 400
        else:
            target_url = image_url
        
        # Download the actual PNG image
        response = requests.get(target_url, timeout=15)
        img = Image.open(io.BytesIO(response.content)).convert('RGBA')
        
        # Downscale to fit your subpixel grid
        img = img.resize((cols, rows), Image.Resampling.LANCZOS)
        
        # Extract RGB values
        pixel_grid = []
        for y in range(rows):
            row_pixels = []
            for x in range(cols):
                r, g, b, a = img.getpixel((x, y))
                # Treat transparent parts as black
                if a <= 15:
                    row_pixels.append([0, 0, 0])
                else:
                    row_pixels.append([r, g, b])
            pixel_grid.append(row_pixels)
            
        return jsonify(pixel_grid)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()
