const express = require('express');
const axios = require('axios');
const { Jimp } = require('jimp');

const app = express();
const PORT = process.env.PORT || 8080;

app.get('/convert', async (req, res) => {
    const assetId = req.query.id;
    const size = parseInt(req.query.width) || 48; // Use width for both dimensions (square)

    if (!assetId) return res.status(400).json({ error: "Missing 'id'" });

    try {
        // 1. Convert Decal ID / Asset ID into a direct raw PNG/JPEG CDN URL
        const thumbApi = `https://thumbnails.roproxy.com/v1/assets?assetIds=${assetId}&returnPolicy=PlaceHolder&size=420x420&format=png`;
        const thumbResponse = await axios.get(thumbApi);
        const imageUrl = thumbResponse.data.data[0].imageUrl;

        if (!imageUrl) throw new Error("Could not fetch Roblox thumbnail");

        // 2. Load and resize image
        const image = await Jimp.read(imageUrl);
        image.resize({ w: size, h: size });

        const pixels = [];

        // 3. Loop through pixels and cull the black/empty ones
        for (let y = 0; y < size; y++) {
            for (let x = 0; x < size; x++) {
                const colorHex = image.getPixelColor(x, y);
                const { r, g, b } = Jimp.intToRGBA(colorHex);

                // Filter out black/dark pixels
                if (r > 15 || g > 15 || b > 15) {
                    pixels.push([x + 1, y + 1, r, g, b]); // 1-based index for Roblox
                }
            }
        }

        res.json({ width: size, height: size, pixels });

    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.listen(PORT, () => console.log(`API Online on port ${PORT}`));
