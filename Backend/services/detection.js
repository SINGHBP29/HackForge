const tf = require('@tensorflow/tfjs-node');
const { embedText } = require('./embedText');
const Sentiment = require('sentiment');
const sentiment = new Sentiment();

const LABELS = ['happy', 'sad', 'anxious'];

// Crisis keywords for offline detection
const CRISIS_KEYWORDS = [
  'suicide','kill myself','end my life','cant go on',"can't go on",
  'want to die','i will die','hurt myself','self harm','self-harm'
];

// Emotion keywords for offline detection
const EMOTION_KEYWORDS = {
  sad: ['sad','depressed','lonely','hopeless','down','unhappy','tear','cry'],
  anxious: ['anxious','nervous','worried','panic','panic attack','stressed','stress'],
  angry: ['angry','mad','furious','annoyed','irritated','hate'],
  happy: ['happy','great','good','glad','awesome','fine','joy','excited']
};

function includesAny(text, arr) {
  return arr.some(k => text.includes(k));
}

let moodModel = null;
async function loadMoodModel() {
  if (!moodModel) {
    try {
      moodModel = await tf.loadLayersModel('file://./models/model-mood-classifier/model.json');
    } catch (err) {
      console.error('Failed to load mood model:', err);
      moodModel = null;
    }
  }
  return moodModel;
}

/**
 * Offline fallback mood detection (rule + sentiment based)
 */
function detectMoodOffline(message) {
  const txt = (message || '').toLowerCase();

  // 1) Crisis detection (highest priority)
  if (includesAny(txt, CRISIS_KEYWORDS)) {
    return { mood: 'crisis', score: null };
  }

  // 2) Sentiment analysis
  const s = sentiment.analyze(txt);
  const score = s.score;

  // 3) Keyword based mood detection
  for (const [mood, keys] of Object.entries(EMOTION_KEYWORDS)) {
    if (includesAny(txt, keys)) {
      return { mood, score };
    }
  }

  // 4) Sentiment threshold fallback
  if (score <= -3) return { mood: 'sad', score };
  if (score <= -1) return { mood: 'anxious', score };
  if (score >= 3) return { mood: 'happy', score };

  return { mood: 'neutral', score };
}

/**
 * Main async detectMood function combining DL model and fallback
 */
async function detectMood(text) {
  if (!text || text.trim().length < 3) {
    // Too short input, use offline detection directly
    return detectMoodOffline(text);
  }

  // Check crisis keywords first (quick safety check)
  if (includesAny(text.toLowerCase(), CRISIS_KEYWORDS)) {
    return { mood: 'crisis', score: null };
  }

  // Attempt to load model & predict with DL model
  const model = await loadMoodModel();

  if (model) {
    try {
      const emb = await embedText(text);
      const inputTensor = tf.tensor2d([emb]);
      const prediction = model.predict(inputTensor);
      const scores = prediction.arraySync()[0];

      const maxIndex = scores.indexOf(Math.max(...scores));
      const mood = LABELS[maxIndex];
      const confidence = scores[maxIndex];

      // If confidence is low, fallback to offline detection
      if (confidence < 0.5) {
        return detectMoodOffline(text);
      }

      return { mood, score: confidence };
    } catch (err) {
      console.error('Error during model prediction:', err);
      // On error, fallback to offline
      return detectMoodOffline(text);
    }
  } else {
    // Model failed to load, fallback to offline
    return detectMoodOffline(text);
  }
}

module.exports = detectMood;
