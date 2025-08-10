# from typing import Optional, Dict
# from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# sentiment = SentimentIntensityAnalyzer()

# CRISIS_KEYWORDS = [
#     'suicide', 'kill myself', 'end my life', 'cant go on', "can't go on",
#     'want to die', 'i will die', 'hurt myself', 'self harm', 'self-harm'
# ]

# EMOTION_KEYWORDS = {
#     'sad': ['sad','depressed','lonely','hopeless','down','unhappy','tear','cry'],
#     'anxious': ['anxious','nervous','worried','panic','panic attack','stressed','stress'],
#     'angry': ['angry','mad','furious','annoyed','irritated','hate'],
#     'happy': ['happy','great','good','glad','awesome','fine','joy','excited']
# }

# def includes_any(text: str, keywords: list[str]) -> bool:
#     return any(k in text for k in keywords)

# def detectMoodOffline(message: Optional[str]) -> Dict[str, Optional[object]]:
#     txt = (message or '').lower()

#     # 1) crisis detection
#     if includes_any(txt, CRISIS_KEYWORDS):
#         return {'mood': 'crisis', 'score': None}

#     # 2) sentiment scoring
#     s = sentiment.polarity_scores(txt)
#     score = int(s['compound'] * 5)  # scale compound score to roughly match original logic

#     # 3) keyword/rule based detection
#     for mood, keys in EMOTION_KEYWORDS.items():
#         if includes_any(txt, keys):
#             return {'mood': mood, 'score': score}

#     # 4) fallback sentiment thresholds
#     if score <= -3:
#         return {'mood': 'sad', 'score': score}
#     if score <= -1:
#         return {'mood': 'anxious', 'score': score}
#     if score >= 3:
#         return {'mood': 'happy', 'score': score}

#     return {'mood': 'neutral', 'score': score}
"""
Mood Detection Service - Analyzes text to detect emotional state and sentiment
Uses VADER sentiment analysis combined with keyword detection
"""

from typing import Optional, Dict, List, Any
import re
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    sentiment = SentimentIntensityAnalyzer()
    HAS_VADER = True
except ImportError:
    print("VADER Sentiment not installed. Install with: pip install vaderSentiment")
    HAS_VADER = False
    sentiment = None

# Crisis keywords (highest priority)
CRISIS_KEYWORDS = [
    'suicide', 'kill myself', 'end my life', 'cant go on', "can't go on",
    'want to die', 'i will die', 'hurt myself', 'self harm', 'self-harm'
]

# Emotion keywords for fallback detection
EMOTION_KEYWORDS = {
    'sad': ['sad','depressed','lonely','hopeless','down','unhappy','tear','cry'],
    'anxious': ['anxious','nervous','worried','panic','panic attack','stressed','stress'],
    'angry': ['angry','mad','furious','annoyed','irritated','hate'],
    'happy': ['happy','great','good','glad','awesome','fine','joy','excited']
}

# Context modifiers
INTENSITY_MODIFIERS = {
    "very": 1.5, "really": 1.4, "extremely": 1.8, "incredibly": 1.6, "absolutely": 1.7,
    "quite": 1.2, "pretty": 1.1, "somewhat": 0.8, "a bit": 0.6, "slightly": 0.5,
    "totally": 1.6, "completely": 1.7, "utterly": 1.8, "deeply": 1.4
}

# Define MOOD_KEYWORDS for advanced mood scoring
MOOD_KEYWORDS = {
    "sad": {
        "emotions": ["sad", "depressed", "down", "unhappy", "hopeless", "miserable"],
        "despair": ["worthless", "useless", "pointless", "empty", "lost"],
        "loss": ["cry", "tear", "lonely", "alone", "abandoned", "grief"],
        "crying": ["crying", "sob", "weep"]
    },
    "anxious": {
        "emotions": ["anxious", "nervous", "worried", "uneasy", "restless"],
        "panic": ["panic", "panic attack", "terrified", "scared", "afraid", "fear"],
        "stress": ["stressed", "stress", "overwhelmed", "tense"]
    },
    "angry": {
        "emotions": ["angry", "mad", "furious", "annoyed", "irritated"],
        "rage": ["rage", "outraged", "enraged", "hate", "resentful"]
    },
    "happy": {
        "emotions": ["happy", "joyful", "joy", "excited", "cheerful", "delighted"],
        "achievement": ["proud", "accomplished", "successful", "confident"],
        "energy": ["energetic", "motivated", "enthusiastic", "optimistic"]
    }
}

NEGATION_WORDS = ["not", "never", "no", "nothing", "nobody", "nowhere", "neither", "none", "can't", "won't", "don't", "isn't", "aren't", "wasn't", "weren't"]

def preprocess_text(text: str) -> str:
    """Clean and normalize text for analysis"""
    # Convert to lowercase
    text = text.lower().strip()
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,!?-]', '', text)
    return text

def detect_crisis_indicators(text: str) -> tuple[bool, float, List[str]]:
    """
    Detect crisis/self-harm indicators in text
    
    Returns:
        Tuple of (is_crisis, severity_score, detected_keywords)
    """
    text_lower = text.lower()
    detected = []
    
    for keyword in CRISIS_KEYWORDS:
        if keyword in text_lower:
            detected.append(keyword)
    
    if detected:
        # High severity if multiple indicators or explicit self-harm language
        severity = 0.9 if len(detected) > 1 or any(word in ["kill myself", "end my life", "suicide"] for word in detected) else 0.8
        return True, severity, detected
    
    return False, 0.0, []

def analyze_sentiment_context(words: List[str], target_index: int) -> float:
    """
    Analyze context around a mood keyword to determine its actual sentiment
    
    Args:
        words: List of words in the text
        target_index: Index of the mood keyword
    
    Returns:
        Context modifier score (-1.0 to 1.0)
    """
    modifier = 1.0
    
    # Check for negation in the 3 words before the target
    start_check = max(0, target_index - 3)
    context_before = words[start_check:target_index]
    
    for word in context_before:
        if word in NEGATION_WORDS:
            modifier = -0.8  # Reverse the sentiment
            break
    
    # Check for intensity modifiers
    for word in context_before:
        if word in INTENSITY_MODIFIERS:
            modifier *= INTENSITY_MODIFIERS[word]
    
    return modifier

def calculate_mood_scores(text: str) -> Dict[str, float]:
    """
    Calculate scores for each mood based on keyword matches
    
    Args:
        text: Preprocessed text
    
    Returns:
        Dictionary with mood scores
    """
    words = text.split()
    mood_scores = {mood: 0.0 for mood in MOOD_KEYWORDS.keys()}
    
    for i, word in enumerate(words):
        for mood, categories in MOOD_KEYWORDS.items():
            for category, keywords in categories.items():
                if word in keywords:
                    # Base score
                    base_score = 1.0
                    
                    # Apply context analysis
                    context_modifier = analyze_sentiment_context(words, i)
                    
                    # Category weights (some categories are stronger indicators)
                    category_weights = {
                        "emotions": 1.2, "despair": 1.5, "panic": 1.4, "rage": 1.3,
                        "achievement": 1.3, "energy": 1.1, "loss": 1.4, "crying": 1.2
                    }
                    category_weight = category_weights.get(category, 1.0)
                    
                    # Calculate final score
                    final_score = base_score * context_modifier * category_weight
                    mood_scores[mood] += final_score
    
    return mood_scores

def includes_any(text: str, keywords: List[str]) -> bool:
    """Check if text contains any of the given keywords"""
    return any(k in text for k in keywords)

def detectMoodOffline(message: Optional[str]) -> Dict[str, Optional[object]]:
    """
    Main mood detection function using VADER sentiment + keyword detection
    
    Args:
        message: Input text to analyze
    
    Returns:
        Dictionary containing mood and score
    """
    if not message:
        return {'mood': 'neutral', 'score': 0}
    
    txt = message.lower()
    
    # 1) Crisis detection (highest priority)
    if includes_any(txt, CRISIS_KEYWORDS):
        return {'mood': 'crisis', 'score': None}
    
    # 2) VADER sentiment scoring
    if HAS_VADER and sentiment:
        s = sentiment.polarity_scores(txt)
        score = int(s['compound'] * 5)  # scale compound score to roughly match original logic
    else:
        # Fallback simple sentiment if VADER not available
        score = _simple_sentiment_score(txt)
    
    # 3) Keyword/rule based detection
    for mood, keys in EMOTION_KEYWORDS.items():
        if includes_any(txt, keys):
            return {'mood': mood, 'score': score}
    
    # 4) Fallback sentiment thresholds
    if score <= -3:
        return {'mood': 'sad', 'score': score}
    if score <= -1:
        return {'mood': 'anxious', 'score': score}
    if score >= 3:
        return {'mood': 'happy', 'score': score}
    
    return {'mood': 'neutral', 'score': score}

def _simple_sentiment_score(text: str) -> int:
    """
    Simple sentiment scoring fallback when VADER is not available
    """
    positive_words = ['good', 'great', 'awesome', 'happy', 'love', 'amazing', 'wonderful', 'excellent', 'fantastic', 'perfect']
    negative_words = ['bad', 'terrible', 'awful', 'hate', 'horrible', 'disgusting', 'worst', 'stupid', 'ugly', 'annoying']
    
    words = text.lower().split()
    positive_count = sum(1 for word in words if word in positive_words)
    negative_count = sum(1 for word in words if word in negative_words)
    
    # Simple scoring
    if positive_count > negative_count:
        return min(5, positive_count * 2)
    elif negative_count > positive_count:
        return max(-5, -negative_count * 2)
    else:
        return 0

# Legacy support for advanced features
def detectEmotionalIntensity(text: str) -> Dict[str, Any]:
    """
    Detect the intensity of emotions in text
    """
    if not text:
        return {"overall_intensity": "neutral", "intensity_breakdown": {}, "intensity_score": 0}
    
    # Check for intensity words
    intensity_words = {
        "high": ["extremely", "incredibly", "absolutely", "completely", "totally", "very", "really"],
        "medium": ["quite", "pretty", "fairly", "rather"],
        "low": ["a bit", "slightly", "somewhat", "kind of"]
    }
    
    text_lower = text.lower()
    detected = {"high": 0, "medium": 0, "low": 0}
    
    for level, words in intensity_words.items():
        for word in words:
            if word in text_lower:
                detected[level] += 1
    
    # Determine overall intensity
    if detected["high"] > 0:
        overall = "high"
    elif detected["medium"] > 0:
        overall = "medium"  
    elif detected["low"] > 0:
        overall = "low"
    else:
        overall = "neutral"
    
    return {
        "overall_intensity": overall,
        "intensity_breakdown": detected,
        "intensity_score": sum(detected.values()) / max(len(text.split()), 1)
    }

def detectMoodAdvanced(text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Advanced mood detection combining VADER with additional analysis
    """
    basic_result = detectMoodOffline(text)
    intensity_result = detectEmotionalIntensity(text)
    
    return {
        **basic_result,
        "intensity": intensity_result,
        "analysis_method": "VADER + keyword detection",
        "has_vader": HAS_VADER
    }