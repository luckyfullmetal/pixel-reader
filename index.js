const express = require('express');
const axios = require('axios');
const sharp = require('sharp');
const app = express();
const PORT = process.env.PORT || 3000;

app.get('/scan-roblox-image', async (req, res) => {
    try {
        const assetId = req.query.id;
        
        // Fetch the public thumbnail via ROProxy
        const thumbnailUrl = `https://thumbnails.roproxy.com/v1/assets?assetIds=${assetId}&returnPolicy=PlaceHolder&size=150x150&format=Png&isCircular=false`;
        const apiResponse = await axios.get(thumbnailUrl, { headers: { 'User-Agent': 'Mozilla/5.0' } });
        
        if (!apiResponse.data || !apiResponse.data.data || apiResponse.data.data.length === 0) {
            throw new Error("No image data found for this Asset ID");
        }
        
        const imageUrl = apiResponse.data.data[0].imageUrl;
        const response = await axios({ url: imageUrl, responseType: 'arraybuffer' });
        
        // Resize to match your physical monitor boundaries
        const { data, info } = await sharp(response.data)
            .resize(296, 156, { fit: 'fill' })
            .raw()
            .toBuffer({ resolveWithObject: true });

        let encodedString = "";
        let currentRun = 1;
        let lastType = "";

        for (let i = 0; i < data.length; i += info.channels) {
            const r = data[i];
            const g = data[i+1];
            const b = data[i+2];

            let type = "K"; // Default to Black

            // HIGH-ACCURACY COLOR EXTRACTION TUNING
            if (r > 140 && g > 140 && b > 140) {
                type = "W"; // White / Light Grays
            } else if (g > r && g > b && g > 40) {
                type = "G"; // Green is dominant channel
            } else if (r > g && r > b && r > 40) {
                type = "R"; // Red is dominant channel
            } else if (b > r && b > g && b > 40) {
                type = "B"; // Blue is dominant channel
            }

            if (i === 0) {
                lastType = type;
                continue;
            }

            if (type === lastType) {
                currentRun++;
            } else {
                encodedString += currentRun + lastType + ",";
                currentRun = 1;
                lastType = type;
            }
        }
        encodedString += currentRun + lastType; 

        res.send(encodedString);
    } catch (error) {
        res.status(500).send("Error: " + error.message);
    }
});

app.listen(PORT, () => console.log(`Pixel Reader online on port ${PORT}`));
