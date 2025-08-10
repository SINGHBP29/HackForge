const express = require('express');
const router = express.Router();
const detectMood = require('../services/moodDetection'); // now async
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
  crisis: [
    "🚨 Your safety matters. Please call a helpline immediately: +91-9152987821"
  ]
};

const MAX_HISTORY = 5;

function updateSession(user_id, mood, keywords, message_text, lastQuestion = null) {
  if (!userSessions[user_id]) {
    userSessions[user_id] = {
      history: [],
      lastQuestion: null,
    };
  }

  userSessions[user_id].history.push({ mood, keywords, message_text, timestamp: new Date().toISOString() });

  if (userSessions[user_id].history.length > MAX_HISTORY) {
    userSessions[user_id].history.shift();
  }

  userSessions[user_id].lastQuestion = lastQuestion;
}

function getLastMoodMention(user_id) {
  const session = userSessions[user_id];
  if (!session || !session.history.length) return null;
  if (session.history.length < 2) return null;

  return session.history[session.history.length - 2];
}

function saveChatData(chatEntry) {
  const filePath = path.join(TEMP_DIR, 'chat_log.jsonl');
  const line = JSON.stringify(chatEntry) + '\n';
  fs.appendFile(filePath, line, (err) => {
    if (err) console.error('Failed to save chat data:', err);
  });
}

// --- UPDATE: make handler async to await detectMood ---
router.post('/respond', async (req, res) => {
  const {
    user_id = 'unknown',
    language = 'en',
    message_text = '',
    media = null
  } = req.body || {};

  if (!message_text.trim() && !media) {
    return res.status(400).json({ error: 'message_text or media is required' });
  }

  // 1) Mood detection & sentiment score (await async detectMood)
  const { mood, score } = await detectMood(message_text);

  // 2) Extract keywords
  const keywords = extractKeywords(message_text);

  // 3) Retrieve previous session info (if any)
  const session = userSessions[user_id] || {};
  const lastQuestion = session.lastQuestion;

  // 4) Save chat entry to offline cache (persistent storage)
  const chatEntry = { user_id, message_text, mood, sentiment_score: score, keywords, timestamp: new Date().toISOString() };
  saveChat(user_id, chatEntry);

  // 5) Retrieve last MAX_HISTORY chat history from offline cache
  const history = getChatHistory(user_id).slice(-MAX_HISTORY);

  // 6) Generate adaptive empathy reply using microservice
  let replyText = getAdaptiveReply(mood, score);

  // 7) Decide follow-up question from your existing logic
  const possibleFollowUps = followUps[mood] || [];
  let followUpQuestion = null;

  if (!lastQuestion) {
    followUpQuestion = possibleFollowUps.length > 0 ? possibleFollowUps[0] : null;
  } else {
    const lastIndex = possibleFollowUps.indexOf(lastQuestion);
    if (lastIndex !== -1 && lastIndex < possibleFollowUps.length - 1) {
      followUpQuestion = possibleFollowUps[lastIndex + 1];
    }
  }

  // 8) Add contextual memory reply enhancement (reference last mood if different)
  const lastMoodMention = getLastMoodMention(user_id);
  if (lastMoodMention && lastMoodMention.mood !== mood) {
    replyText += ` By the way, last time you mentioned feeling ${lastMoodMention.mood}. How are things now?`;
  }

  // 9) Append follow-up question
  if (followUpQuestion) {
    replyText += ' ' + followUpQuestion;
  }

  // 10) If media present, acknowledge in reply
  if (media && media.mimetype) {
    const mediaType = media.mimetype.split('/')[0];
    if (mediaType === 'image') {
      replyText += ' Thanks for sharing that image! 📸';
    } else if (mediaType === 'video') {
      replyText += ' Thanks for sharing the video! 🎥';
    } else {
      replyText += ' Thanks for sharing the media!';
    }
  }

  // 11) Crisis mode overrides reply and disables follow-ups
  if (mood === 'crisis') {
    replyText = replyTemplates.crisis[0];
    followUpQuestion = null;
  }

  // 12) Every MAX_HISTORY messages, add a memory summary TL;DR to reply
  let memorySummary = null;
  if (history.length >= MAX_HISTORY) {
    memorySummary = summarizeChat(history);
    replyText += `\n\nQuick summary: ${memorySummary}`;
  }

  // 13) Update session with current data
  updateSession(user_id, mood, keywords, message_text, followUpQuestion);

  // 14) Log interaction with color
  const colorFn = colorMap[mood] || chalk.white;
  console.log(
    colorFn(`[${new Date().toISOString()}] (${mood.toUpperCase()}) ${user_id}: ${message_text}`) +
    (media ? ` [Media: ${media.originalName || 'unknown'}]` : '')
  );

  // 15) Save chat data temporarily (same as before)
  saveChatData({
    timestamp: new Date().toISOString(),
    user_id,
    message_text,
    mood,
    sentiment_score: score,
    keywords,
    reply_text: replyText
  });

  // 16) Send JSON response
  res.json({
    user_id,
    mood,
    sentiment_score: score,
    keywords,
    reply_text: replyText.trim(),
    crisis: mood === 'crisis',
    media,
  });
});

module.exports = router;
