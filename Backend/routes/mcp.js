// routes/mcp.js
const express = require('express');
const router = express.Router();
const detectMoodOffline = require('../services/moodDetection'); // ✅ Correct import
const nlp = require('compromise');
const chalk = require('chalk');
const path = require('path');
const fs = require('fs');

// Microservices imports
const { getAdaptiveReply } = require('../microservices/empathyService');
const { summarizeChat } = require('../microservices/memorySummaryService');
const { saveChat, getChatHistory } = require('../microservices/offlineCacheService');
// Add these at the top, near your imports or constants:
const BEARER_TOKEN = 'abc123';
const myNumber = '+918982777971'; // Replace with your real number

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
    happy: [
        "What else has made you smile recently?",
        "Do you want to share more good news?"
    ],
    sad: [
        "Would you like to talk about what's troubling you?",
        "Can I help you find ways to feel better?"
    ],
    anxious: [
        "What do you think is making you anxious?",
        "Want to try a quick relaxation exercise together?"
    ],
    neutral: [
        "Anything new or interesting on your mind today?",
        "Would you like to share something fun or relaxing?"
    ]
};
const replyTemplates = {
    crisis: ["🚨 Your safety matters. Please call a helpline immediately: +91-9152987821"]
};
const MAX_HISTORY = 5;

function extractKeywords(text) {
    try {
        const doc = nlp(text);
        const nouns = doc.nouns().out('array') || [];
        return Array.from(
            new Set(nouns.map(s => s.toLowerCase().trim()).filter(Boolean))
        ).slice(0, 3);
    } catch {
        return [];
    }
}

function updateSession(user_id, mood, keywords, message_text, lastQuestion = null) {
    if (!userSessions[user_id]) {
        userSessions[user_id] = { history: [], lastQuestion: null };
    }
    userSessions[user_id].history.push({
        mood,
        keywords,
        message_text,
        timestamp: new Date().toISOString()
    });
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

// POST /mcp/respond
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

    const { mood, score } = detectMoodOffline(message_text);
    const keywords = extractKeywords(message_text);
    const session = userSessions[user_id] || {};
    const lastQuestion = session.lastQuestion;

    const chatEntry = {
        user_id,
        message_text,
        mood,
        sentiment_score: score,
        keywords,
        timestamp: new Date().toISOString()
    };
    saveChat(user_id, chatEntry);

    const history = getChatHistory(user_id).slice(-MAX_HISTORY);
    let replyText = getAdaptiveReply(mood, score);

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
        followUpQuestion = null;
    }

    if (history.length >= MAX_HISTORY) {
        const memorySummary = summarizeChat(history);
        replyText += `\n\nQuick summary: ${memorySummary}`;
    }

    updateSession(user_id, mood, keywords, message_text, followUpQuestion);

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

// Middleware for MCP routes except /respond to check bearer token and route tools
router.use((req, res, next) => {
  // Skip token check for /respond route
  if (req.path === '/respond') {
    return next();
  }

  // Check Authorization header for Bearer token
  const authHeader = req.headers['authorization'];
  if (!authHeader || authHeader !== `Bearer ${BEARER_TOKEN}`) {
    return res.status(401).json({ error: 'Unauthorized: Invalid bearer token' });
  }
  next();
});

// New MCP tool handler at POST /mcp (root) for tools like validate
router.post('/', express.json(), (req, res) => {
  const { tool } = req.body;

  if (tool === 'validate') {
    return res.json({ result: myNumber });
  }

  res.status(400).json({ error: 'Unknown tool' });
});

module.exports = router;
