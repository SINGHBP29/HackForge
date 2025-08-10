import json
from datetime import datetime, timezone
from typing import Optional, Any
from pathlib import Path

import spacy
from colorama import Fore, Style, init

from microservices.empathyService import getAdaptiveReply
from microservices.memorySummaryService import summarizeChat
from microservices.offlineCacheService import saveChat, getChatHistory
from services.moodDetection import detectMoodOffline

init(autoreset=True)
nlp = spacy.load("en_core_web_sm")

TEMP_DIR = Path(__file__).parent.parent / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Session data and constants
user_sessions = {}
MAX_HISTORY = 5
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

@router.post("/respond")
async def respond(request: Request):
    try:
        data = await request.json()
        return JSONResponse(content={
            "status": "success",
            "echo": data,
            "message": "MCP server received the request!"
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# You can keep your respond() function here or import it
# (Just rename or separate your business logic from FastAPI endpoints)


color_map = {
    "crisis": lambda text: Fore.RED + text + Style.RESET_ALL,
    "sad": lambda text: Fore.BLUE + text + Style.RESET_ALL,
    "happy": lambda text: Fore.GREEN + text + Style.RESET_ALL,
    "anxious": lambda text: Fore.YELLOW + text + Style.RESET_ALL,
    "neutral": lambda text: Fore.WHITE + text + Style.RESET_ALL,
}

follow_ups = {
    "happy": [
        "What else has made you smile recently?",
        "Do you want to share more good news?",
    ],
    "sad": [
        "Would you like to talk about what's troubling you?",
        "Can I help you find ways to feel better?",
    ],
    "anxious": [
        "What do you think is making you anxious?",
        "Want to try a quick relaxation exercise together?",
    ],
    "neutral": [
        "Anything new or interesting on your mind today?",
        "Would you like to share something fun or relaxing?",
    ],
}

reply_templates = {
    "crisis": ["🚨 Your safety matters. Please call a helpline immediately: +91-9152987821"]
}

def extract_keywords(text: str) -> list[str]:
    try:
        doc = nlp(text)
        nouns = [token.text.lower().strip() for token in doc if token.pos_ == "NOUN" and token.text.strip()]
        keywords = list(dict.fromkeys(nouns))  # unique nouns preserving order
        return keywords[:3]
    except Exception:
        return []

def update_session(user_id: str, mood: str, keywords: list[str], message_text: str, last_question: Optional[str] = None):
    if user_id not in user_sessions:
        user_sessions[user_id] = {"history": [], "last_question": None}
    user_sessions[user_id]["history"].append({
        "mood": mood,
        "keywords": keywords,
        "message_text": message_text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    if len(user_sessions[user_id]["history"]) > MAX_HISTORY:
        user_sessions[user_id]["history"].pop(0)
    user_sessions[user_id]["last_question"] = last_question

def get_last_mood_mention(user_id: str) -> Optional[dict[str, Any]]:
    session = user_sessions.get(user_id)
    if not session or len(session["history"]) < 2:
        return None
    return session["history"][-2]

def save_chat_data(chat_entry: dict[str, Any]):
    file_path = TEMP_DIR / "chat_log.jsonl"
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(chat_entry) + "\n")
    except Exception as e:
        print(f"Failed to save chat data: {e}")

async def respond(
    user_id: str = "unknown",
    message_text: str = "",
    media: Optional[dict] = None,
) -> dict:
    message_text = message_text.strip()
    if not message_text and not media:
        raise ValueError("message_text or media is required")

    # Detect mood and score
    mood_data = detectMoodOffline(message_text)
    mood = mood_data.get("mood", "neutral")
    score = mood_data.get("score", 0.0)

    # Extract keywords
    keywords = extract_keywords(message_text)

    # Load user session info
    session = user_sessions.get(user_id, {})
    last_question = session.get("last_question")

    # Log chat entry to offline cache
    chat_entry = {
        "user_id": user_id,
        "message_text": message_text,
        "mood": mood,
        "sentiment_score": score,
        "keywords": keywords,
        "timestamp": datetime.utcnow().isoformat(),
    }
    await saveChat(user_id, chat_entry)

    # Retrieve history and get adaptive reply
    history = getChatHistory(user_id)[-MAX_HISTORY:]
    reply_text = getAdaptiveReply(mood, score)

    # Prepare follow-up questions
    possible_follow_ups = follow_ups.get(mood, [])
    follow_up_question = None
    if not last_question and possible_follow_ups:
        follow_up_question = possible_follow_ups[0]
    elif last_question in possible_follow_ups:
        idx = possible_follow_ups.index(last_question)
        if idx < len(possible_follow_ups) - 1:
            follow_up_question = possible_follow_ups[idx + 1]

    # Compare with last mood mention
    last_mood_mention = get_last_mood_mention(user_id)
    if last_mood_mention and last_mood_mention.get("mood") != mood:
        reply_text += f" By the way, last time you mentioned feeling {last_mood_mention.get('mood')}. How are things now?"

    # Append follow-up question
    if follow_up_question:
        reply_text += " " + follow_up_question

    # Handle media types
    if media and "mimetype" in media:
        media_type = media["mimetype"].split("/")[0]
        if media_type == "image":
            reply_text += " Thanks for sharing that image! 📸"
        elif media_type == "video":
            reply_text += " Thanks for sharing the video! 🎥"
        else:
            reply_text += " Thanks for sharing the media!"

    # Handle crisis mood specifically
    if mood == "crisis":
        reply_text = reply_templates["crisis"][0]
        follow_up_question = None

    # Summarize chat history if long enough
    if len(history) >= MAX_HISTORY:
        memory_summary = summarizeChat(history)
        reply_text += f"\n\nQuick summary: {memory_summary}"

    # Update session with current interaction
    update_session(user_id, mood, keywords, message_text, follow_up_question)

    # Log to console with colors
    color_fn = color_map.get(mood, color_map["neutral"])
    print(color_fn(f"[{datetime.now(timezone.utc).isoformat()}] ({mood.upper()}) {user_id}: {message_text}") +
          (f" [Media: {media.get('originalName', 'unknown')}]" if media else ""))
    # Save chat log locally
    save_chat_data({
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "message_text": message_text,
        "mood": mood,
        "sentiment_score": score,
        "keywords": keywords,
        "reply_text": reply_text,
    })

    # Return structured response
    return {
        "user_id": user_id,
        "mood": mood,
        "sentiment_score": score,
        "keywords": keywords,
        "reply_text": reply_text.strip(),
        "crisis": mood == "crisis",
        "media": media,
    }