const translate = require('@vitalets/google-translate-api');

async function translateText(text, targetLang, detect = false) {
    try {
        const res = await translate(text, { to: targetLang });
        if (detect) {
            return { text: res.text, lang: res.from.language.iso };
        }
        return res.text;
    } catch (err) {
        console.error("Translation error:", err);
        return text; // Fallback to original text
    }
}

module.exports = translateText;
