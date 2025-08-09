// const express = require('express');
// const router = express.Router();
// const detectMood = require('../services/moodDetection');
// const getResponse = require('../services/response');

// router.post('/respond', (req, res) => {
//     const { user_id, language = 'en', message_text } = req.body;

//     if (!message_text) {
//         return res.status(400).json({ error: 'message_text is required' });
//     }

//     const mood = detectMood(message_text);
//     const reply = getResponse(mood, language);

//     res.json({
//         user_id,
//         mood,
//         reply_text: reply.text,
//         quick_replies: reply.quickReplies
//     });
// });

// module.exports = router;
const express = require('express');
const router = express.Router();
const detectMood = require('../services/moodDetection');
const getResponse = require('../services/response');
const translateText = require('../services/translator');
const Sentiment = require('sentiment');
const sentiment = new Sentiment();

router.post('/respond', async (req, res) => {
    try {
        const { user_id, language = 'auto', message_text } = req.body;

        if (!message_text) {
            return res.status(400).json({ error: 'message_text is required' });
        }

        // Step 1: Translate if not English
        let processedText = message_text;
        let detectedLang = language;
        if (language === 'auto') {
            const { text, lang } = await translateText(message_text, 'en', true);
            processedText = text;
            detectedLang = lang;
        } else if (language !== 'en') {
            processedText = await translateText(message_text, 'en');
        }

        // Step 2: NLP Mood Detection
        const mood = detectMood(processedText);

        // Step 3: Sentiment Score
        const sentimentScore = sentiment.analyze(processedText).score;

        // Step 4: Get AI-style response
        const reply = getResponse(mood, 'en', sentimentScore);

        res.json({
            success: true,
            user_id,
            detected_language: detectedLang,
            mood,
            sentiment_score: sentimentScore,
            reply_text: reply.text,
            quick_replies: reply.quickReplies
        });
    } catch (err) {
        console.error(err);
        res.status(500).json({ error: 'Server error', details: err.message });
    }
});

module.exports = router;

