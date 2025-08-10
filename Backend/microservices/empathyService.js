// empathyService.js
const replyTemplates = {
  happy: {
    mild: ["😊 You're doing great! Keep shining!"],
    strong: ["🌟 Wow, that's amazing! Keep the joy flowing!"]
  },
  sad: {
    mild: ["💙 I understand, I'm here if you want to talk."],
    strong: ["💔 That sounds tough, remember you're not alone."]
  },
  anxious: {
    mild: ["😌 Try to breathe deeply, it’ll help."],
    strong: ["😟 I'm here with you. Let's work through this together."]
  },
  neutral: {
    mild: ["🙂 What's on your mind?"],
    strong: ["👋 Hope things get better soon!"]
  }
};

function getAdaptiveReply(mood, sentimentScore) {
  // Define thresholds arbitrarily, customize as needed
  const threshold = 0.5;
  const intensity = Math.abs(sentimentScore) > threshold ? 'strong' : 'mild';
  const responses = replyTemplates[mood] || replyTemplates.neutral;
  const options = responses[intensity];
  return options[Math.floor(Math.random() * options.length)];
}

module.exports = { getAdaptiveReply };
