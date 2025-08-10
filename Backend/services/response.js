// function getResponse(mood, lang) {
//     const responses = {
//         en: {
//             happy: {
//                 text: "😊 I'm glad to hear that! Keep spreading positivity!",
//                 quickReplies: ["Mindfulness Exercise", "Motivational Video"]
//             },
//             sad: {
//                 text: "💙 I’m here for you. It’s okay to feel this way. You’re not alone.",
//                 quickReplies: ["Helpline", "Coping Tips", "Motivational Video"]
//             },
//             anxious: {
//                 text: "😌 Take a deep breath. Try a 5-minute mindfulness exercise?",
//                 quickReplies: ["Mindfulness Exercise", "Helpline"]
//             },
//             crisis: {
//                 text: "🚨 Your safety matters. Please call a helpline immediately: +1-800-273-8255 (US), +91-9152987821 (India)",
//                 quickReplies: ["Helpline", "Crisis Support"]
//             },
//             neutral: {
//                 text: "👋 Hey! How’s your day going?",
//                 quickReplies: ["Mindfulness Exercise", "Coping Tips"]
//             }
//         }
//     };

//     return responses[lang][mood] || responses[lang]['neutral'];
// }

// module.exports = getResponse;

// function getResponse(mood, lang, sentimentScore) {
//     const responses = {
//         en: {
//             happy: {
//                 text: "😊 That's wonderful! Keep sharing your good vibes with the world!",
//                 quickReplies: ["Mindfulness Exercise", "Motivational Video", "Gratitude Journal"]
//             },
//             sad: {
//                 text: "💙 I hear you. It’s okay to feel this way — you’re not alone.",
//                 quickReplies: ["Helpline", "Coping Tips", "Guided Meditation"]
//             },
//             anxious: {
//                 text: "😌 Let’s slow down together. How about trying a 5-minute deep breathing exercise?",
//                 quickReplies: ["Mindfulness Exercise", "Helpline", "Positive Affirmations"]
//             },
//             crisis: {
//                 text: "🚨 Your safety matters most. Please reach out right now: AASRA India Helpline +91-9820466726 or 988 helpline (India).",
//                 quickReplies: ["Call Helpline", "Crisis Support"]
//             },
//             neutral: {
//                 text: "👋 Hi there! How’s your day going?",
//                 quickReplies: ["Mindfulness Exercise", "Coping Tips", "Share Something Good"]
//             }
//         }
//     };

//     // Extra personalization based on sentiment score
//     if (sentimentScore <= -3 && mood !== 'crisis') {
//         return {
//             text: responses[lang][mood].text + " Remember, tough times don’t last — you do. 💪",
//             quickReplies: responses[lang][mood].quickReplies
//         };
//     }

//     return responses[lang][mood] || responses[lang]['neutral'];
// }

// module.exports = getResponse;

// services/response.js
// Dynamic response generator: templates, personalization, quick replies
const templates = {
  en: {
    happy: [
      "😊 That's wonderful to hear! Keep that energy going.",
      "🎉 Love to hear you’re feeling good — care to share why?"
    ],
    sad: [
      "💙 I’m sorry you’re feeling down. Would you like a quick grounding exercise?",
      "I hear you — it’s okay to feel this. Want some coping tips?"
    ],
    anxious: [
      "😌 Let’s try a 3-step breathing exercise to calm down. Want to try?",
      "Anxiety can be overwhelming. Would you like a short mindfulness guide?"
    ],
    angry: [
      "🔥 It seems like you’re upset. Want a quick release technique?",
      "I’m listening — do you want a calming exercise or ways to channel that anger?"
    ],
    neutral: [
      "👋 I’m here — tell me what’s on your mind.",
      "Hi! Want a quick mindfulness exercise or some tips?"
    ],
    crisis: [
      "🚨 If you are in immediate danger or thinking of self-harm, please call your local emergency number or helpline now. For India: AASRA +91-9820466726.",
      "Your safety matters. If you're at risk, call emergency services immediately."
    ]
  },
  // small Hindi support (demo). Expand as needed.
  hi: {
    happy: ["😊 Acha sunke khushi hui! Apna khayal rakho."],
    sad: ["💙 Aap akela nahi hain. Kuch madad chahiye?"],
    anxious: ["😌 Gehri saans len — chahte ho main guide karoon?"],
    crisis: ["🚨 Sankat ki sthiti mein turant apne local helpline ko call karein: +91-9820466726"]
  }
};

// quick reply options by mood
const quickRepliesMap = {
  happy: ["Share why", "Mindfulness Exercise"],
  sad: ["Coping Tips", "Helpline", "Guided Meditation"],
  anxious: ["Breathing Exercise", "Guided Meditation", "Helpline"],
  angry: ["Calming Exercise", "Write it down"],
  neutral: ["Mindfulness Exercise", "Coping Tips"],
  crisis: ["Call Helpline", "Emergency Contacts"]
};

function pickRandom(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

/**
 * getResponse(mood, lang, opts)
 * - mood: string from detectMoodOffline
 * - lang: 'en' or 'hi' etc. (fallback to en)
 * - opts: { keywords: [], sentimentScore }
 */
function getResponse(mood, lang = 'en', opts = {}) {
  const language = templates[lang] ? lang : 'en';
  const tpool = templates[language][mood] || templates[language]['neutral'];
  let text = pickRandom(tpool);

  // personalization: insert first keyword if available
  if (opts.keywords && opts.keywords.length > 0) {
    const first = opts.keywords[0];
    // keep it simple and friendly
    text = `${text} (${first ? `about ${first}` : ''})`.trim();
  }

  // sentiment-based warmth
  if (typeof opts.sentimentScore === 'number' && opts.sentimentScore <= -4 && mood !== 'crisis') {
    text = `${text} Remember, this too shall pass — you're not alone.`;
  }

  return {
    text,
    quickReplies: quickRepliesMap[mood] || quickRepliesMap['neutral']
  };
}

module.exports = getResponse;

