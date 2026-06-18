const express = require('express');
const axios = require('axios');
const sharp = require('sharp');
const app = express();
const PORT = process.env.PORT || 3000;

app.get('/scan-roblox-image', async (req, res) => {
    try {
        const response = await axios({ url: `https://assetdelivery.roblox.com/v1/asset/?id=${req.query.id}`, responseType: 'arraybuffer' });
        const { data, info } = await sharp(response.data).resize(296, 156, { fit: 'fill' }).raw().toBuffer({ resolveWithObject: true });
        let encodedString = "", currentRun = 1, lastType = "";
        for (let i = 0; i < data.length; i += info.channels) {
            let type = "K";
            if (data[i] > 180 && data[i+1] > 180 && data[i+2] > 180) type = "W";
            else if (data[i] > 120 && data[i+1] < 80 && data[i+2] < 80) type = "R";
            else if (data[i+2] > 120 && data[i] < 80 && data[i+1] < 80) type = "B";
            if (i === 0) { lastType = type; continue; }
            if (type === lastType) { currentRun++; } else { encodedString += currentRun + lastType + ","; currentRun = 1; lastType = type; }
        }
        res.send(encodedString + currentRun + lastType);
    } catch (error) { res.status(500).send("Error: " + error.message); }
});
app.listen(PORT);
