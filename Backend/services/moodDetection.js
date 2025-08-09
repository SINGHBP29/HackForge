// function detectMood(message) {
//     const lower = message.toLowerCase();

//     if (lower.includes('suicide') || lower.includes('kill myself')) return 'crisis';
//     if (lower.includes('sad') || lower.includes('depressed') || lower.includes('lonely')) return 'sad';
//     if (lower.includes('anxious') || lower.includes('worried')) return 'anxious';
//     if (lower.includes('happy') || lower.includes('good') || lower.includes('great')) return 'happy';

//     return 'neutral';
// }

// module.exports = detectMood;

function detectMood(message) {
    const lower = message.toLowerCase();

    const crisisWords = [
        'suicide', 'kill myself', 'end my life', 'can’t go on', 'self harm'
    ];
    if (crisisWords.some(word => lower.includes(word))) return 'crisis';
    if (lower.includes('sad') || lower.includes('depressed') || lower.includes('lonely')) return 'sad';
    if (lower.includes('anxious') || lower.includes('worried') || lower.includes('nervous')) return 'anxious';
    if (lower.includes('happy') || lower.includes('good') || lower.includes('great')) return 'happy';

    return 'neutral';
}

module.exports = detectMood;

