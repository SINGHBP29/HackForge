"""
Memory Summary Service - Summarizes chat history and user patterns
"""

from typing import List, Dict, Any
from collections import Counter
from datetime import datetime, timezone
import json

def summarizeChat(chat_history: List[Dict[str, Any]]) -> str:
    """
    Summarize the chat history to provide context for ongoing conversations
    
    Args:
        chat_history: List of chat entries with mood, keywords, messages, etc.
    
    Returns:
        str: A concise summary of the chat history
    """
    if not chat_history:
        return "No previous conversation history."
    
    if len(chat_history) == 1:
        entry = chat_history[0]
        mood = entry.get('mood', 'neutral')
        return f"You mentioned feeling {mood} earlier."
    
    # Analyze mood patterns
    moods = [entry.get('mood', 'neutral') for entry in chat_history]
    mood_counts = Counter(moods)
    most_common_mood = mood_counts.most_common(1)[0][0]
    
    # Analyze keywords
    all_keywords = []
    for entry in chat_history:
        keywords = entry.get('keywords', [])
        if keywords:
            all_keywords.extend(keywords)
    
    keyword_counts = Counter(all_keywords)
    top_keywords = [kw for kw, count in keyword_counts.most_common(3)]
    
    # Build summary
    summary_parts = []
    
    # Mood summary
    if len(set(moods)) == 1:
        summary_parts.append(f"You've consistently been feeling {most_common_mood}")
    else:
        mood_variety = list(set(moods))
        if len(mood_variety) == 2:
            summary_parts.append(f"Your mood has shifted between {' and '.join(mood_variety)}")
        else:
            summary_parts.append(f"You've experienced various emotions: {', '.join(mood_variety[:3])}")
    
    # Keywords summary
    if top_keywords:
        if len(top_keywords) == 1:
            summary_parts.append(f"You've been talking about {top_keywords[0]}")
        elif len(top_keywords) == 2:
            summary_parts.append(f"Main topics have been {' and '.join(top_keywords)}")
        else:
            summary_parts.append(f"You've mentioned {', '.join(top_keywords[:-1])}, and {top_keywords[-1]}")
    
    # Time-based context
    if len(chat_history) >= 3:
        summary_parts.append("We've had a good conversation going")
    
    return ". ".join(summary_parts) + "."

def getConversationInsights(chat_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get deeper insights about the user's conversation patterns
    
    Args:
        chat_history: List of chat entries
    
    Returns:
        Dict containing conversation insights
    """
    if not chat_history:
        return {"insights": "No conversation data available"}
    
    moods = [entry.get('mood', 'neutral') for entry in chat_history]
    keywords = []
    for entry in chat_history:
        keywords.extend(entry.get('keywords', []))
    
    mood_distribution = dict(Counter(moods))
    keyword_frequency = dict(Counter(keywords))
    
    # Calculate mood trends
    mood_trend = "stable"
    if len(moods) >= 3:
        recent_moods = moods[-3:]
        if all(mood in ['sad', 'anxious', 'crisis'] for mood in recent_moods):
            mood_trend = "concerning"
        elif all(mood in ['happy', 'neutral'] for mood in recent_moods):
            mood_trend = "positive"
        elif len(set(recent_moods)) > 2:
            mood_trend = "fluctuating"
    
    # Identify conversation themes
    themes = []
    theme_keywords = {
        "relationships": ["friend", "family", "partner", "love", "relationship"],
        "work_school": ["work", "job", "school", "study", "boss", "teacher"],
        "health": ["health", "sick", "pain", "doctor", "medicine"],
        "personal_growth": ["goal", "dream", "future", "change", "improve"],
        "stress": ["stress", "pressure", "overwhelmed", "busy", "tired"]
    }
    
    for theme, theme_words in theme_keywords.items():
        if any(kw.lower() in [k.lower() for k in keywords] for kw in theme_words):
            themes.append(theme)
    
    return {
        "total_messages": len(chat_history),
        "mood_distribution": mood_distribution,
        "dominant_mood": max(mood_distribution, key=mood_distribution.get),
        "mood_trend": mood_trend,
        "top_keywords": list(Counter(keywords).most_common(5)),
        "conversation_themes": themes,
        "needs_attention": mood_trend == "concerning",
        "session_length": "extended" if len(chat_history) > 10 else "brief"
    }

def generatePersonalizedGreeting(chat_history: List[Dict[str, Any]]) -> str:
    """
    Generate a personalized greeting based on conversation history
    
    Args:
        chat_history: Previous conversation history
    
    Returns:
        str: Personalized greeting
    """
    if not chat_history:
        return "Hello! I'm here to listen and support you."
    
    last_entry = chat_history[-1]
    last_mood = last_entry.get('mood', 'neutral')
    
    if last_mood == 'crisis':
        return "I'm glad you're reaching out again. How are you feeling right now?"
    elif last_mood == 'sad':
        return "Hello again. I hope you're feeling a bit better since we last talked."
    elif last_mood == 'happy':
        return "Hi there! I hope you're still feeling as positive as when we last spoke."
    elif last_mood == 'anxious':
        return "Hello! I hope some of that anxiety has settled since our last conversation."
    else:
        return "Good to hear from you again. What's on your mind today?"

def trackProgressOverTime(chat_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Track user's emotional progress over time
    
    Args:
        chat_history: Conversation history with timestamps
    
    Returns:
        Dict with progress analysis
    """
    if len(chat_history) < 3:
        return {"status": "insufficient_data", "message": "Need more conversation history to track progress"}
    
    # Sort by timestamp if available
    sorted_history = sorted(chat_history, key=lambda x: x.get('timestamp', ''))
    
    mood_scores = {
        'crisis': -2,
        'sad': -1,
        'anxious': -0.5,
        'neutral': 0,
        'happy': 1
    }
    
    scores = [mood_scores.get(entry.get('mood', 'neutral'), 0) for entry in sorted_history]
    
    # Calculate trend
    if len(scores) >= 3:
        recent_avg = sum(scores[-3:]) / 3
        earlier_avg = sum(scores[:-3]) / len(scores[:-3]) if len(scores) > 3 else sum(scores[:3]) / 3
        
        if recent_avg > earlier_avg + 0.3:
            trend = "improving"
        elif recent_avg < earlier_avg - 0.3:
            trend = "declining" 
        else:
            trend = "stable"
    else:
        trend = "stable"
    
    return {
        "trend": trend,
        "current_score": scores[-1] if scores else 0,
        "average_score": sum(scores) / len(scores) if scores else 0,
        "mood_stability": "stable" if len(set([entry.get('mood') for entry in sorted_history[-5:]])) <= 2 else "fluctuating",
        "total_interactions": len(chat_history)
    }