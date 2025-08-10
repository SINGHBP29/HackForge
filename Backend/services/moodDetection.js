// function detectMood(message) {
//     const lower = message.toLowerCase();

//     if (lower.includes('suicide') || lower.includes('kill myself')) return 'crisis';
//     if (lower.includes('sad') || lower.includes('depressed') || lower.includes('lonely')) return 'sad';
//     if (lower.includes('anxious') || lower.includes('worried')) return 'anxious';
//     if (lower.includes('happy') || lower.includes('good') || lower.includes('great')) return 'happy';

//     return 'neutral';
// }

// module.exports = detectMood;

// function detectMood(message) {
//     const lower = message.toLowerCase();

//     const crisisWords = [
//         'suicide', 'kill myself', 'end my life', 'can’t go on', 'self harm'
//     ];
//     if (crisisWords.some(word => lower.includes(word))) return 'crisis';
//     if (lower.includes('sad') || lower.includes('depressed') || lower.includes('lonely')) return 'sad';
//     if (lower.includes('anxious') || lower.includes('worried') || lower.includes('nervous')) return 'anxious';
//     if (lower.includes('happy') || lower.includes('good') || lower.includes('great')) return 'happy';

//     return 'neutral';
// }

// module.exports = detectMood;

// services/moodDetection.js
const Sentiment = require('sentiment');
const sentiment = new Sentiment();

// Expanded crisis & emotion keywords
const CRISIS_KEYWORDS = [
  'suicide','kill myself','end my life','cant go on','can\'t go on','want to die','i will die','hurt myself','self harm','self-harm'
];

const EMOTION_KEYWORDS = {
  sad: ['sad','depressed','lonely','hopeless','down','unhappy','tear','cry'],
  anxious: ['anxious','nervous','worried','panic','panic attack','stressed','stress'],
  angry: ['angry','mad','furious','annoyed','irritated','hate'],
  happy: ['happy','great','good','glad','awesome','fine','joy','excited']
};

function includesAny(text, arr) {
  return arr.some(k => text.includes(k));
}

/**
 * detectMoodOffline
 * - returns: { mood: 'sad'|'anxious'|'angry'|'happy'|'neutral'|'crisis', score: sentimentScore }
 */
function detectMoodOffline(message) {
  const txt = (message || '').toLowerCase();

  // 1) crisis detection (highest priority)
  if (includesAny(txt, CRISIS_KEYWORDS)) {
    return { mood: 'crisis', score: null };
  }

  // 2) sentiment scoring
  const s = sentiment.analyze(txt);
  const score = s.score; // negative = negative sentiment

  // 3) keyword / rule-based detection
  for (const [mood, keys] of Object.entries(EMOTION_KEYWORDS)) {
    if (includesAny(txt, keys)) {
      return { mood, score };
    }
  }

  // 4) fallback using sentiment thresholds
  if (score <= -3) return { mood: 'sad', score };
  if (score <= -1) return { mood: 'anxious', score };
  if (score >= 3) return { mood: 'happy', score };

  return { mood: 'neutral', score };
}

module.exports = detectMoodOffline;


