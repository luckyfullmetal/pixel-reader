const express = require('express');
const axios = require('axios');
const sharp = require('sharp');
const app = express();
const PORT = process.env.PORT || 3000;

app.get('/scan-roblox-image', async (req, res) => {
    try {
        const assetId = req.query.id;
        
        // Use the Public Thumbnail endpoint - completely bypasses unauthenticated file download blocks!
        const thumbnailUrl = `https://thumbnails.roproxy.com/v1/assets?assetIds=${assetId}&returnPolicy=PlaceHolder&size=150x150&format=Png&isCircular=false`;
        
        const apiResponse = await axios.get(thumbnailUrl, { headers: { 'User-Agent': 'Mozilla/5.0' } });
        
        if (!apiResponse.data || !apiResponse.data.data || apiResponse.data.data.length === 0) {
            throw new Error("No image data found for this Asset ID");
        }
        
        const imageUrl = apiResponse.data.data[0].imageUrl;
        
        // Fetch the raw image buffer securely
        const response = await axios({ url: imageUrl, responseType: 'arraybuffer' });
        
        // Resize perfectly to your screen dimensions
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

            let type = "K"; 
            if (r > 150 && g > 150 && b > 150) type = "W"; 
            else if (r > 120 && g < 90 && b < 90) type = "R";   
            else if (b > 120 && r < 90 && g < 90) type = "B";   

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
