const express = require('express');
const router = express.Router();
const detectMood = require('../services/moodDetection');
const nlp = require('compromise');
const chalk = require('chalk');
const path = require('path');
const fs = require('fs');

// Microservices imports
const { getAdaptiveReply } = require('../microservices/empathyService');
const { summarizeChat } = require('../microservices/memorySummaryService');
const { saveChat, getChatHistory } = require('../microservices/offlineCacheService');

const TEMP_DIR = path.join(__dirname, '../temp');
if (!fs.existsSync(TEMP_DIR)) {
    fs.mkdirSync(TEMP_DIR, { recursive: true });
}

const userSessions = {};
const colorMap = {
    crisis: chalk.red,
    sad: chalk.blue,
    happy: chalk.green,
    anxious: chalk.yellow,
    neutral: chalk.white
};
const followUps = {
    happy: ["What else has made you smile recently?", "Do you want to share more good news?"],
    sad: ["Would you like to talk about what's troubling you?", "Can I help you find ways to feel better?"],
    anxious: ["What do you think is making you anxious?", "Want to try a quick relaxation exercise together?"],
    neutral: ["Anything new or interesting on your mind today?", "Would you like to share something fun or relaxing?"]
};
const replyTemplates = {
    crisis: ["🚨 Your safety matters. Please call a helpline immediately: +91-9152987821"]
};
const MAX_HISTORY = 5;

function extractKeywords(text) {
    try {
        const doc = nlp(text);
        const nouns = doc.nouns().out('array') || [];
        const filtered = Array.from(new Set(nouns.map(s => s.toLowerCase().trim()).filter(Boolean)));
        return filtered.slice(0, 3);
    } catch (e) {
        return [];
    }
}

function updateSession(user_id, mood, keywords, message_text, lastQuestion = null) {
    if (!userSessions[user_id]) {
        userSessions[user_id] = { history: [], lastQuestion: null };
    }
    userSessions[user_id].history.push({ mood, keywords, message_text, timestamp: new Date().toISOString() });
    if (userSessions[user_id].history.length > MAX_HISTORY) {
        userSessions[user_id].history.shift();
    }
    userSessions[user_id].lastQuestion = lastQuestion;
}

function getLastMoodMention(user_id) {
    const session = userSessions[user_id];
    if (!session || session.history.length < 2) return null;
    return session.history[session.history.length - 2];
}

function saveChatData(chatEntry) {
    const filePath = path.join(TEMP_DIR, 'chat_log.jsonl');
    fs.appendFile(filePath, JSON.stringify(chatEntry) + '\n', (err) => {
        if (err) console.error('Failed to save chat data:', err);
    });
}

router.post('/respond', (req, res) => {
    const {
        user_id = 'unknown',
        language = 'en',
        message_text = '',
        media = null
    } = req.body || {};

    if (!message_text.trim() && !media) {
        return res.status(400).json({ error: 'message_text or media is required' });
    }

    // --- Detect mood ---
    const { mood, score } = detectMood(message_text);
    const keywords = extractKeywords(message_text);
    const session = userSessions[user_id] || {};
    const lastQuestion = session.lastQuestion;

    // --- Detect if user is asking a question ---
    const lowerMsg = message_text.toLowerCase();
    const isQuestion = message_text.trim().endsWith('?') ||
        /\b(what|why|how|when|where|who|can|should|do you|could)\b/i.test(lowerMsg);

    const chatEntry = { user_id, message_text, mood, sentiment_score: score, keywords, timestamp: new Date().toISOString() };
    saveChat(user_id, chatEntry);

    const history = getChatHistory(user_id).slice(-MAX_HISTORY);
    let replyText;

    if (isQuestion) {
        // Direct Q&A style reply
        replyText = `That's a great question! Based on your mood (${mood}), here's my take: ${getAdaptiveReply(mood, score)}`;
    } else {
        // Normal mood-based response flow
        replyText = getAdaptiveReply(mood, score);

        const possibleFollowUps = followUps[mood] || [];
        let followUpQuestion = null;
        if (!lastQuestion) {
            followUpQuestion = possibleFollowUps[0] || null;
        } else {
            const lastIndex = possibleFollowUps.indexOf(lastQuestion);
            if (lastIndex !== -1 && lastIndex < possibleFollowUps.length - 1) {
                followUpQuestion = possibleFollowUps[lastIndex + 1];
            }
        }

        const lastMoodMention = getLastMoodMention(user_id);
        if (lastMoodMention && lastMoodMention.mood !== mood) {
            replyText += ` By the way, last time you mentioned feeling ${lastMoodMention.mood}. How are things now?`;
        }

        if (followUpQuestion) {
            replyText += ' ' + followUpQuestion;
        }

        if (media && media.mimetype) {
            const mediaType = media.mimetype.split('/')[0];
            if (mediaType === 'image') replyText += ' Thanks for sharing that image! 📸';
            else if (mediaType === 'video') replyText += ' Thanks for sharing the video! 🎥';
            else replyText += ' Thanks for sharing the media!';
        }

        if (mood === 'crisis') {
            replyText = replyTemplates.crisis[0];
        }

        if (history.length >= MAX_HISTORY) {
            const memorySummary = summarizeChat(history);
            replyText += `\n\nQuick summary: ${memorySummary}`;
        }

        updateSession(user_id, mood, keywords, message_text, followUpQuestion);
    }

    const colorFn = colorMap[mood] || chalk.white;
    console.log(colorFn(`[${new Date().toISOString()}] (${mood.toUpperCase()}) ${user_id}: ${message_text}`) +
        (media ? ` [Media: ${media.originalName || 'unknown'}]` : ''));

    saveChatData({
        timestamp: new Date().toISOString(),
        user_id,
        message_text,
        mood,
        sentiment_score: score,
        keywords,
        reply_text: replyText
    });

    res.json({
        user_id,
        mood,
        sentiment_score: score,
        keywords,
        reply_text: replyText.trim(),
        crisis: mood === 'crisis',
        media
    });
});

module.exports = router;
