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

function getResponse(mood, lang, sentimentScore) {
    const responses = {
        en: {
            happy: {
                text: "😊 That's wonderful! Keep sharing your good vibes with the world!",
                quickReplies: ["Mindfulness Exercise", "Motivational Video", "Gratitude Journal"]
            },
            sad: {
                text: "💙 I hear you. It’s okay to feel this way — you’re not alone.",
                quickReplies: ["Helpline", "Coping Tips", "Guided Meditation"]
            },
            anxious: {
                text: "😌 Let’s slow down together. How about trying a 5-minute deep breathing exercise?",
                quickReplies: ["Mindfulness Exercise", "Helpline", "Positive Affirmations"]
            },
            crisis: {
                text: "🚨 Your safety matters most. Please reach out right now: AASRA India Helpline +91-9820466726 or 988 helpline (India).",
                quickReplies: ["Call Helpline", "Crisis Support"]
            },
            neutral: {
                text: "👋 Hi there! How’s your day going?",
                quickReplies: ["Mindfulness Exercise", "Coping Tips", "Share Something Good"]
            }
        }
    };

    // Extra personalization based on sentiment score
    if (sentimentScore <= -3 && mood !== 'crisis') {
        return {
            text: responses[lang][mood].text + " Remember, tough times don’t last — you do. 💪",
            quickReplies: responses[lang][mood].quickReplies
        };
    }

    return responses[lang][mood] || responses[lang]['neutral'];
}

module.exports = getResponse;
