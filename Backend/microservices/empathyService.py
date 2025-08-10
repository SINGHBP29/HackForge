"""
Empathy Service - Generates adaptive replies based on mood and sentiment score
"""

import random
from typing import Dict, List

def getAdaptiveReply(mood: str, score: float = 0.0) -> str:
    """
    Generate an empathetic reply based on detected mood and sentiment score
    
    Args:
        mood: The detected mood (happy, sad, anxious, neutral, crisis)
        score: Sentiment score (-1.0 to 1.0, negative is more negative sentiment)
    
    Returns:
        str: An appropriate empathetic response
    """
    
    # Crisis responses (highest priority)
    if mood == "crisis":
        crisis_responses = [
            "I'm really concerned about you right now. Your safety is the most important thing.",
            "It sounds like you're going through an incredibly difficult time. Please reach out for immediate help.",
            "I can hear that you're in a lot of pain. You don't have to go through this alone.",
        ]
        return random.choice(crisis_responses)
    
    # Happy responses
    elif mood == "happy":
        if score > 0.7:  # Very positive
            happy_responses = [
                "That's absolutely wonderful! I can feel your joy through your words! ✨",
                "Your happiness is contagious! It sounds like things are going really well for you.",
                "I'm so glad to hear you're feeling this good! You deserve all this happiness.",
                "What amazing news! Your positive energy really comes through.",
            ]
        else:  # Moderately positive
            happy_responses = [
                "That's really nice to hear! I'm glad you're feeling good today.",
                "It's lovely that you're in good spirits! Tell me more about what's making you happy.",
                "I can sense the positivity in your message. That's wonderful!",
                "It sounds like you're having a good day, and that makes me happy too.",
            ]
        return random.choice(happy_responses)
    
    # Sad responses
    elif mood == "sad":
        if score < -0.6:  # Very negative
            sad_responses = [
                "I can really hear the pain in your words, and I want you to know that I'm here with you.",
                "It sounds like you're carrying a heavy burden right now. That must feel overwhelming.",
                "I'm so sorry you're going through this difficult time. Your feelings are completely valid.",
                "Thank you for sharing something so personal with me. I can sense how much you're hurting.",
            ]
        else:  # Moderately sad
            sad_responses = [
                "I can hear that you're feeling down, and I want you to know that's okay.",
                "It sounds like you're having a tough time. I'm here to listen.",
                "I'm sorry you're feeling this way. Sometimes we all need someone to talk to.",
                "Your feelings are completely understandable. Thank you for sharing with me.",
            ]
        return random.choice(sad_responses)
    
    # Anxious responses
    elif mood == "anxious":
        if score < -0.5:  # High anxiety
            anxious_responses = [
                "I can sense you're feeling really overwhelmed right now. Let's take this one step at a time.",
                "It sounds like your mind is racing with worries. That must be exhausting.",
                "I hear the anxiety in your words, and I want you to know that what you're feeling is valid.",
                "It seems like you're carrying a lot of stress. Remember that it's okay to take breaks.",
            ]
        else:  # Moderate anxiety
            anxious_responses = [
                "I can tell you're feeling a bit anxious. That's completely normal and understandable.",
                "It sounds like something is weighing on your mind. Would you like to talk about it?",
                "I sense some worry in your message. Sometimes it helps just to voice our concerns.",
                "I can feel that you're a bit unsettled. Thank you for sharing that with me.",
            ]
        return random.choice(anxious_responses)
    
    # Neutral responses
    else:  # neutral or unknown mood
        neutral_responses = [
            "Thank you for sharing that with me. I'm here to listen and support you.",
            "I appreciate you taking the time to reach out. How are you feeling overall?",
            "It's good to hear from you. I'm here if you need someone to talk to.",
            "Thanks for sharing. I'm listening and here to support you in whatever way I can.",
            "I'm glad you reached out today. What's on your mind?",
        ]
        return random.choice(neutral_responses)

def getContextualResponse(mood: str, keywords: List[str], user_history: List[Dict] = None) -> str:
    """
    Generate a more contextual response based on mood, keywords, and user history
    
    Args:
        mood: Detected mood
        keywords: Extracted keywords from the message
        user_history: Previous conversation history
    
    Returns:
        str: Contextual empathetic response
    """
    base_response = getAdaptiveReply(mood)
    
    # Add contextual elements based on keywords
    keyword_responses = {
        "work": "It sounds like work is on your mind. Balancing work life can be challenging.",
        "family": "Family relationships can bring both joy and stress. I'm here to listen.",
        "school": "School can be overwhelming sometimes. You're doing your best.",
        "friend": "Friendships are so important. It's good that you have people you care about.",
        "health": "Your health and wellbeing are so important. I hope you're taking care of yourself.",
        "money": "Financial stress can be really overwhelming. Those worries are completely valid.",
        "relationship": "Relationships can be complex and emotionally intense. I'm here to support you.",
    }
    
    # Look for relevant keywords and add contextual response
    for keyword in keywords:
        keyword_lower = keyword.lower()
        for key, response in keyword_responses.items():
            if key in keyword_lower or keyword_lower in key:
                base_response += f" {response}"
                break
    
    return base_response

# For backward compatibility
def generate_empathy_response(mood: str, score: float = 0.0) -> str:
    """Alias for getAdaptiveReply for backward compatibility"""
    return getAdaptiveReply(mood, score)