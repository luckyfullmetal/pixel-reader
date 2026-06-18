const express = require('express');
const axios = require('axios');
const sharp = require('sharp');
const app = express();
const PORT = process.env.PORT || 3000;

app.get('/scan-roblox-image', async (req, res) => {
    try {
        const assetId = req.query.id;
        
        // ROUTE VIA ROProxy: Bypasses direct user-agent blocks on asset delivery networks
        const proxyUrl = `https://assetdelivery.roproxy.com/v1/asset/?id=${assetId}`;
        
        const response = await axios({ 
            url: proxyUrl, 
            responseType: 'arraybuffer',
            headers: { 'User-Agent': 'Mozilla/5.0' } // Simulates standard browser access
        });
        
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
            if (r > 160 && g > 160 && b > 160) type = "W"; 
            else if (r > 110 && g < 90 && b < 90) type = "R";   
            else if (b > 110 && r < 90 && g < 90) type = "B";   

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

app.listen(PORT, () => console.log(`Pixel Reader live on port ${PORT}`));
