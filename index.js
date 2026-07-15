const express = require('express');
const axios = require('axios');
const { Jimp } = require('jimp');

const app = express();
const PORT = process.env.PORT || 8080;

// Helper function to resolve a Roblox Asset ID to its direct CDN asset URL
async function getRobloxImageUrl(assetId) {
    const deliveryUrl = `https://assetdelivery.roblox.com/v1/asset/?id=${assetId}`;
    try {
        const response = await axios.get(deliveryUrl, { maxRedirects: 5 });
        return response.request.res.responseUrl;
    } catch (err) {
        // Fallback directly to the asset endpoint if resolution fails
        return `https://assetdelivery.roblox.com/v1/asset/?id=${assetId}`;
    }
}

app.get('/convert', async (req, res) => {
    const assetId = req.query.id;
    const width = parseInt(req.query.width) || 48;
    const height = parseInt(req.query.height) || 48;

    if (!assetId) {
        return res.status(400).json({ error: "Missing 'id' parameter" });
    }

    try {
        // 1. Get the actual CDN image URL from Roblox
        const imgUrl = await getRobloxImageUrl(assetId);

        // 2. Load and resize the image using Jimp
        const image = await Jimp.read(imgUrl);
        image.resize({ w: width, h: height });

        const pixelData = [];

        // 3. Loop through every pixel
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                // Get color at coordinates (0-indexed in Jimp)
                const colorHex = image.getPixelColor(x, y);
                const { r, g, b } = Jimp.intToRGBA(colorHex);

                // DYNAMIC SKIP: Skip dark/black pixels to optimize network data
                if (r > 12 || g > 12 || b > 12) {
                    // Store as [X, Y, R, G, B] (Converting to 1-based index for Roblox Luau)
                    pixelData.push([x + 1, y + 1, r, g, b]);
                }
            }
        }

        // 4. Return coordinates & dimensions
        res.json({
            width: width,
            height: height,
            pixels: pixelData
        });

    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.listen(PORT, () => {
    console.log(`OLED conversion API running on port ${PORT}`);
});
