const express = require('express');
const axios = require('axios');
const sharp = require('sharp');
const app = express();
const PORT = process.env.PORT || 3000;

app.get('/scan-roblox-image', async (req, res) => {
    try {
        const assetId = req.query.id;
        const thumbnailUrl = `https://thumbnails.roproxy.com/v1/assets?assetIds=${assetId}&returnPolicy=PlaceHolder&size=150x150&format=Png&isCircular=false`;
        const apiResponse = await axios.get(thumbnailUrl, { headers: { 'User-Agent': 'Mozilla/5.0' } });
        
        if (!apiResponse.data || !apiResponse.data.data || apiResponse.data.data.length === 0) {
            throw new Error("No image data found for this Asset ID");
        }
        
        const imageUrl = apiResponse.data.data[0].imageUrl;
        const response = await axios({ url: imageUrl, responseType: 'arraybuffer' });
        
        // Exact high-density matrix dimensions
        const { data, info } = await sharp(response.data)
            .resize(592, 312, { fit: 'fill' })
            .raw()
            .toBuffer({ resolveWithObject: true });

        let encodedString = "";
        for (let i = 0; i < data.length; i += info.channels) {
            encodedString += `${data[i]}.${data[i+1]}.${data[i+2]},`;
        }
        
        res.send(encodedString.slice(0, -1));
    } catch (error) {
        res.status(500).send("Error: " + error.message);
    }
});

app.listen(PORT, () => console.log(`High-Density Pixel Reader online on port ${PORT}`));
