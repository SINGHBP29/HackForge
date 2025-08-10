// memorySummaryService.js
const nlp = require('compromise');

function summarizeChat(history) {
  // history = array of { message_text, mood }

  // Aggregate moods count
  const moodCount = history.reduce((acc, entry) => {
    acc[entry.mood] = (acc[entry.mood] || 0) + 1;
    return acc;
  }, {});

  // Extract frequent keywords across messages
  const allKeywords = history.flatMap(h => {
    const doc = nlp(h.message_text);
    return doc.nouns().out('array').map(s => s.toLowerCase());
  });

  // Count keywords frequency
  const keywordFreq = allKeywords.reduce((acc, word) => {
    acc[word] = (acc[word] || 0) + 1;
    return acc;
  }, {});

  // Pick top 3 keywords
  const topKeywords = Object.entries(keywordFreq)
    .sort((a,b) => b[1] - a[1])
    .slice(0,3)
    .map(([k]) => k);

  // Compose summary
  const dominantMood = Object.entries(moodCount)
    .sort((a,b) => b[1] - a[1])[0][0];

  return `You’ve mostly been feeling ${dominantMood} lately, talking about ${topKeywords.join(', ')}. How does that sound?`;
}

module.exports = { summarizeChat };
