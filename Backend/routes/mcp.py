#!/usr/bin/env python3
"""
Mental Health Support MCP Server - Python Implementation
Provides empathetic responses and mood analysis using MCP protocol
"""

import asyncio
import json
# import os  # Removed unused import
import sys
import hashlib
import random
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Sequence
from collections import Counter

# MCP SDK imports
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from fastapi import APIRouter, Request
from typing import Optional

router = APIRouter()

@router.post("/respond")
async def respond_endpoint(request: Request):
    data = await request.json()
    user_id = data.get("user_id", "unknown")
    message_text = data.get("message_text", "")
    media = data.get("media", None)
    # Call the respond() method from the MentalHealthMCP instance
    mcp_server = MentalHealthMCP()
    response = await mcp_server.respond({
        "user_id": user_id,
        "message_text": message_text,
        "media": media
    })
    return response

# Colorama for colored console output
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    HAS_COLORAMA = True
except ImportError:
    print("Colorama not available. Install with: pip install colorama")
    HAS_COLORAMA = False

# VADER Sentiment Analysis
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    sentiment_analyzer = SentimentIntensityAnalyzer()
    HAS_VADER = True
except ImportError:
    print("VADER Sentiment not available. Install with: pip install vaderSentiment")
    HAS_VADER = False
    sentiment_analyzer = None

# SpaCy for advanced NLP (optional)
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    HAS_SPACY = True
except (ImportError, OSError):
    print("SpaCy not available. Install with: pip install spacy && python -m spacy download en_core_web_sm")
    HAS_SPACY = False
    nlp = None


class MentalHealthMCP:
    """Mental Health Support MCP Server with empathetic response generation"""
    
    def __init__(self):
        # Constants
        self.BEARER_TOKEN = "abc123"
        self.MY_NUMBER = "+918982777971"
        self.MAX_HISTORY = 5
        
        # Initialize directories
        self.TEMP_DIR = Path(__file__).parent.parent / "temp"
        self.CACHE_DIR = Path(__file__).parent.parent / "cache"
        self.USER_DATA_DIR = self.CACHE_DIR / "users"
        self.GLOBAL_CACHE_FILE = self.CACHE_DIR / "global_chat_log.jsonl"
        
        self._ensure_directories()
        
        # Session management
        self.user_sessions = {}
        
        # Crisis keywords (highest priority)
        self.CRISIS_KEYWORDS = [
            'suicide', 'kill myself', 'end my life', 'cant go on', "can't go on",
            'want to die', 'i will die', 'hurt myself', 'self harm', 'self-harm',
            'no point living', 'better off dead', 'ending it all'
        ]
        
        # Emotion keywords
        self.EMOTION_KEYWORDS = {
            'sad': ['sad', 'depressed', 'lonely', 'hopeless', 'down', 'unhappy', 'tear', 'cry', 'miserable'],
            'anxious': ['anxious', 'nervous', 'worried', 'panic', 'panic attack', 'stressed', 'stress', 'overwhelmed'],
            'angry': ['angry', 'mad', 'furious', 'annoyed', 'irritated', 'hate', 'rage', 'outraged'],
            'happy': ['happy', 'great', 'good', 'glad', 'awesome', 'fine', 'joy', 'excited', 'wonderful']
        }
        
        # Color mapping for console output
        if HAS_COLORAMA:
            self.color_map = {
                "crisis": lambda text: Fore.RED + text + Style.RESET_ALL,
                "sad": lambda text: Fore.BLUE + text + Style.RESET_ALL,
                "happy": lambda text: Fore.GREEN + text + Style.RESET_ALL,
                "anxious": lambda text: Fore.YELLOW + text + Style.RESET_ALL,
                "neutral": lambda text: Fore.WHITE + text + Style.RESET_ALL,
            }
        else:
            self.color_map = {
                "crisis": lambda text: f"[CRISIS] {text}",
                "sad": lambda text: f"[SAD] {text}",
                "happy": lambda text: f"[HAPPY] {text}",
                "anxious": lambda text: f"[ANXIOUS] {text}",
                "neutral": lambda text: f"[NEUTRAL] {text}",
            }
        
        # Follow-up questions
        self.follow_ups = {
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
        
        # Reply templates
        self.reply_templates = {
            "crisis": ["🚨 Your safety matters. Please call a helpline immediately: +91-9152987821"]
        }
        
        # Initialize MCP server
        self.server = Server("mental-health-support-mcp")
        self._setup_handlers()
    
    def _ensure_directories(self):
        """Create necessary directories"""
        self.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    def _setup_handlers(self):
        """Setup MCP server handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> List[types.Tool]:
            return [
                types.Tool(
                    name="respond",
                    description="Generate empathetic responses based on mood and sentiment analysis",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "Unique identifier for the user",
                                "default": "unknown"
                            },
                            "language": {
                                "type": "string", 
                                "description": "Language preference",
                                "default": "en"
                            },
                            "message_text": {
                                "type": "string",
                                "description": "The user message to analyze and respond to"
                            },
                            "media": {
                                "type": "object",
                                "description": "Optional media attachment",
                                "properties": {
                                    "mimetype": {"type": "string"},
                                    "originalName": {"type": "string"},
                                    "data": {"type": "string"}
                                }
                            }
                        },
                        "required": []
                    }
                ),
                types.Tool(
                    name="validate",
                    description="Validate the server and return contact number",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    }
                ),
                types.Tool(
                    name="get_user_stats",
                    description="Get user conversation statistics and insights",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "Unique identifier for the user"
                            }
                        },
                        "required": ["user_id"]
                    }
                ),
                types.Tool(
                    name="clear_user_data",
                    description="Clear all data for a specific user",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "Unique identifier for the user"
                            }
                        },
                        "required": ["user_id"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> Sequence[types.TextContent]:
            try:
                if name == "respond":
                    result = await self.respond(arguments)
                    return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
                elif name == "validate":
                    return [types.TextContent(type="text", text=self.MY_NUMBER)]
                elif name == "get_user_stats":
                    user_id = arguments.get("user_id", "")
                    if not user_id:
                        raise ValueError("user_id is required")
                    stats = await self.get_user_statistics(user_id)
                    return [types.TextContent(type="text", text=json.dumps(stats, indent=2))]
                elif name == "clear_user_data":
                    user_id = arguments.get("user_id", "")
                    if not user_id:
                        raise ValueError("user_id is required")
                    success = await self.clear_user_data(user_id)
                    return [types.TextContent(type="text", text=f"Data cleared: {success}")]
                else:
                    raise ValueError(f"Unknown tool: {name}")
            except Exception as error:
                return [types.TextContent(type="text", text=f"Error: {str(error)}")]
    
    # Mood Detection Service
    def detect_mood_offline(self, message: Optional[str]) -> Dict[str, Any]:
        """
        Main mood detection function using VADER sentiment + keyword detection
        """
        if not message:
            return {'mood': 'neutral', 'score': 0}
        
        txt = message.lower()
        
        # 1) Crisis detection (highest priority)
        if self._includes_any(txt, self.CRISIS_KEYWORDS):
            return {'mood': 'crisis', 'score': None}
        
        # 2) VADER sentiment scoring
        if HAS_VADER and sentiment_analyzer:
            s = sentiment_analyzer.polarity_scores(txt)
            score = int(s['compound'] * 5)  # scale compound score
        else:
            # Fallback simple sentiment if VADER not available
            score = self._simple_sentiment_score(txt)
        
        # 3) Keyword/rule based detection
        for mood, keywords in self.EMOTION_KEYWORDS.items():
            if self._includes_any(txt, keywords):
                return {'mood': mood, 'score': score}
        
        # 4) Fallback sentiment thresholds
        if score <= -3:
            return {'mood': 'sad', 'score': score}
        if score <= -1:
            return {'mood': 'anxious', 'score': score}
        if score >= 3:
            return {'mood': 'happy', 'score': score}
        
        return {'mood': 'neutral', 'score': score}
    
    def _includes_any(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the given keywords"""
        return any(keyword in text for keyword in keywords)
    
    def _simple_sentiment_score(self, text: str) -> int:
        """Simple sentiment scoring fallback when VADER is not available"""
        positive_words = ['good', 'great', 'awesome', 'happy', 'love', 'amazing', 'wonderful', 'excellent', 'fantastic', 'perfect']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'horrible', 'disgusting', 'worst', 'stupid', 'ugly', 'annoying']
        
        words = text.lower().split()
        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)
        
        if positive_count > negative_count:
            return min(5, positive_count * 2)
        elif negative_count > positive_count:
            return max(-5, -negative_count * 2)
        else:
            return 0
    
    # Empathy Service
    def get_adaptive_reply(self, mood: str, score: float = 0.0) -> str:
        """Generate an empathetic reply based on detected mood and sentiment score"""
        
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
        else:
            neutral_responses = [
                "Thank you for sharing that with me. I'm here to listen and support you.",
                "I appreciate you taking the time to reach out. How are you feeling overall?",
                "It's good to hear from you. I'm here if you need someone to talk to.",
                "Thanks for sharing. I'm listening and here to support you in whatever way I can.",
                "I'm glad you reached out today. What's on your mind?",
            ]
            return random.choice(neutral_responses)
    
    # Keyword Extraction
    def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text using SpaCy or simple fallback"""
        try:
            if HAS_SPACY and nlp:
                doc = nlp(text)
                nouns = [token.text.lower().strip() for token in doc 
                        if token.pos_ == "NOUN" and token.text.strip()]
                keywords = list(dict.fromkeys(nouns))  # Remove duplicates while preserving order
                return keywords[:3]
            else:
                # Fallback keyword extraction
                words = re.sub(r'[^\w\s]', ' ', text.lower()).split()
                words = [word for word in words if len(word) > 3 and 
                        word not in ['this', 'that', 'with', 'have', 'will', 'from', 'they', 'been', 'said', 'each', 'which', 'their']]
                keywords = list(dict.fromkeys(words))[:3]
                return keywords
        except Exception as e:
            print(f"Error extracting keywords: {e}")
            return []
    
    # File Management
    def _get_user_file(self, user_id: str) -> Path:
        """Get the file path for a specific user's data"""
        hashed_id = hashlib.md5(user_id.encode()).hexdigest()
        return self.USER_DATA_DIR / f"user_{hashed_id}.json"
    
    async def _load_user_data(self, user_id: str) -> Dict[str, Any]:
        """Load user data from file"""
        user_file = self._get_user_file(user_id)
        if user_file.exists():
            try:
                async with asyncio.to_thread(open, user_file, 'r', encoding='utf-8') as f:
                    content = await asyncio.to_thread(f.read)
                    return json.loads(content)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading user data for {user_id}: {e}")
        return {"user_id": user_id, "chat_history": [], "metadata": {}}
    
    async def _save_user_data(self, user_id: str, data: Dict[str, Any]) -> bool:
        """Save user data to file"""
        user_file = self._get_user_file(user_id)
        try:
            data["last_updated"] = datetime.now(timezone.utc).isoformat()
            async with asyncio.to_thread(open, user_file, 'w', encoding='utf-8') as f:
                await asyncio.to_thread(f.write, json.dumps(data, indent=2, ensure_ascii=False))
            return True
        except IOError as e:
            print(f"Error saving user data for {user_id}: {e}")
            return False
    
    async def save_chat(self, user_id: str, chat_entry: Dict[str, Any]) -> bool:
        """Save a chat entry for a specific user"""
        try:
            if "timestamp" not in chat_entry:
                chat_entry["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            user_data = await self._load_user_data(user_id)
            user_data["chat_history"].append(chat_entry)
            
            if "metadata" not in user_data:
                user_data["metadata"] = {}
            
            user_data["metadata"].update({
                "total_messages": len(user_data["chat_history"]),
                "last_interaction": chat_entry["timestamp"],
                "last_mood": chat_entry.get("mood", "neutral")
            })
            
            success = await self._save_user_data(user_id, user_data)
            
            if success:
                await self._save_to_global_log(user_id, chat_entry)
            
            return success
        except Exception as e:
            print(f"Error in save_chat for user {user_id}: {e}")
            return False
    
    async def _save_to_global_log(self, user_id: str, chat_entry: Dict[str, Any]):
        """Save chat entry to global log file"""
        try:
            global_entry = {
                "user_id_hash": hashlib.md5(user_id.encode()).hexdigest()[:8],
                **chat_entry
            }
            
            async with asyncio.to_thread(open, self.GLOBAL_CACHE_FILE, 'a', encoding='utf-8') as f:
                await asyncio.to_thread(f.write, json.dumps(global_entry) + '\n')
        except Exception as e:
            print(f"Error saving to global log: {e}")
    
    async def get_chat_history(self, user_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get chat history for a specific user"""
        try:
            user_data = await self._load_user_data(user_id)
            history = user_data.get("chat_history", [])
            
            # Sort by timestamp
            history.sort(key=lambda x: x.get("timestamp", ""))
            
            if limit:
                return history[-limit:]
            
            return history
        except Exception as e:
            print(f"Error getting chat history for user {user_id}: {e}")
            return []
    
    # Memory Summary Service
    def summarize_chat(self, chat_history: List[Dict[str, Any]]) -> str:
        """Summarize the chat history to provide context for ongoing conversations"""
        if not chat_history:
            return "No previous conversation history."
        
        if len(chat_history) == 1:
            mood = chat_history[0].get('mood', 'neutral')
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
        unique_moods = list(set(moods))
        if len(unique_moods) == 1:
            summary_parts.append(f"You've consistently been feeling {most_common_mood}")
        elif len(unique_moods) == 2:
            summary_parts.append(f"Your mood has shifted between {' and '.join(unique_moods)}")
        else:
            summary_parts.append(f"You've experienced various emotions: {', '.join(unique_moods[:3])}")
        
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
    
    # Session Management
    def update_session(self, user_id: str, mood: str, keywords: List[str], 
                      message_text: str, last_question: Optional[str] = None):
        """Update user session with latest interaction"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {"history": [], "last_question": None}
        
        self.user_sessions[user_id]["history"].append({
            "mood": mood,
            "keywords": keywords,
            "message_text": message_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        if len(self.user_sessions[user_id]["history"]) > self.MAX_HISTORY:
            self.user_sessions[user_id]["history"].pop(0)
        
        self.user_sessions[user_id]["last_question"] = last_question
    
    def get_last_mood_mention(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the last mood mention from session history"""
        session = self.user_sessions.get(user_id)
        if not session or len(session["history"]) < 2:
            return None
        return session["history"][-2]
    
    async def save_chat_data(self, chat_entry: Dict[str, Any]):
        """Save chat data to temporary log file"""
        file_path = self.TEMP_DIR / "chat_log.jsonl"
        try:
            async with asyncio.to_thread(open, file_path, "a", encoding="utf-8") as f:
                await asyncio.to_thread(f.write, json.dumps(chat_entry) + "\n")
        except Exception as e:
            print(f"Failed to save chat data: {e}")
    
    # User Statistics and Analytics
    async def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user statistics and insights"""
        try:
            user_data = await self._load_user_data(user_id)
            history = user_data.get("chat_history", [])
            
            if not history:
                return {"status": "no_data", "message": "No conversation history found"}
            
            # Mood analysis
            moods = [entry.get("mood", "neutral") for entry in history]
            mood_distribution = dict(Counter(moods))
            
            # Keywords analysis
            all_keywords = []
            for entry in history:
                all_keywords.extend(entry.get("keywords", []))
            keyword_frequency = dict(Counter(all_keywords))
            
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
            
            # Conversation themes
            themes = self._identify_conversation_themes(all_keywords)
            
            return {
                "user_id": user_id,
                "total_messages": len(history),
                "mood_distribution": mood_distribution,
                "dominant_mood": max(mood_distribution, key=mood_distribution.get) if mood_distribution else "neutral",
                "mood_trend": mood_trend,
                "top_keywords": list(Counter(all_keywords).most_common(5)),
                "conversation_themes": themes,
                "needs_attention": mood_trend == "concerning",
                "session_length": "extended" if len(history) > 10 else "brief",
                "metadata": user_data.get("metadata", {})
            }
        except Exception as e:
            print(f"Error getting user statistics for {user_id}: {e}")
            return {"error": str(e)}
    
    def _identify_conversation_themes(self, keywords: List[str]) -> List[str]:
        """Identify conversation themes from keywords"""
        themes = []
        theme_keywords = {
            "relationships": ["friend", "family", "partner", "love", "relationship"],
            "work_school": ["work", "job", "school", "study", "boss", "teacher"],
            "health": ["health", "sick", "pain", "doctor", "medicine"],
            "personal_growth": ["goal", "dream", "future", "change", "improve"],
            "stress": ["stress", "pressure", "overwhelmed", "busy", "tired"]
        }
        
        keywords_lower = [kw.lower() for kw in keywords]
        
        for theme, theme_words in theme_keywords.items():
            if any(tw.lower() in keywords_lower for tw in theme_words):
                themes.append(theme)
        
        return themes
    
    async def clear_user_data(self, user_id: str) -> bool:
        """Clear all data for a specific user"""
        try:
            user_file = self._get_user_file(user_id)
            if user_file.exists():
                await asyncio.to_thread(user_file.unlink)
            
            # Clear from memory sessions
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            
            return True
        except Exception as e:
            print(f"Error clearing data for user {user_id}: {e}")
            return False
    
    # Main Response Handler
    async def respond(self, args: Dict[str, Any] = None) -> Dict[str, Any]:
        """Main response handler - analyzes mood and generates empathetic responses"""
        if args is None:
            args = {}
        
        user_id = args.get("user_id", "unknown")
        language = args.get("language", "en")
        message_text = args.get("message_text", "").strip()
        media = args.get("media")
        
        if not message_text and not media:
            raise ValueError("message_text or media is required")
        
        # Detect mood and sentiment
        mood_data = self.detect_mood_offline(message_text)
        mood = mood_data.get("mood", "neutral")
        score = mood_data.get("score", 0.0)
        
        # Extract keywords
        keywords = self.extract_keywords(message_text)
        
        # Get session info
        session = self.user_sessions.get(user_id, {})
        last_question = session.get("last_question")
        
        # Create chat entry
        chat_entry = {
            "user_id": user_id,
            "message_text": message_text,
            "mood": mood,
            "sentiment_score": score,
            "keywords": keywords,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Save to persistent storage
        await self.save_chat(user_id, chat_entry)
        
        # Get recent history
        history = await self.get_chat_history(user_id, self.MAX_HISTORY)
        
        # Generate empathetic reply
        reply_text = self.get_adaptive_reply(mood, score)
        
        # Handle follow-up questions
        possible_follow_ups = self.follow_ups.get(mood, [])
        follow_up_question = None
        
        if not last_question and possible_follow_ups:
            follow_up_question = possible_follow_ups[0]
        elif last_question and last_question in possible_follow_ups:
            idx = possible_follow_ups.index(last_question)
            if idx < len(possible_follow_ups) - 1:
                follow_up_question = possible_follow_ups[idx + 1]
        
        # Reference previous mood if different
        last_mood_mention = self.get_last_mood_mention(user_id)
        if last_mood_mention and last_mood_mention.get("mood") != mood:
            reply_text += f" By the way, last time you mentioned feeling {last_mood_mention.get('mood')}. How are things now?"
        
        # Add follow-up question
        if follow_up_question:
            reply_text += " " + follow_up_question
        
        # Handle media
        if media and media.get("mimetype"):
            media_type = media["mimetype"].split("/")[0]
            if media_type == "image":
                reply_text += " Thanks for sharing that image! 📸"
            elif media_type == "video":
                reply_text += " Thanks for sharing the video! 🎥"
            else:
                reply_text += " Thanks for sharing the media!"
        
        # Crisis override
        if mood == "crisis":
            reply_text = self.reply_templates["crisis"][0]
            follow_up_question = None
        
        # Add memory summary for long conversations
        if len(history) >= self.MAX_HISTORY:
            memory_summary = self.summarize_chat(history)
            reply_text += f"\n\nQuick summary: {memory_summary}"
        
        # Update session
        self.update_session(user_id, mood, keywords, message_text, follow_up_question)
        
        # Console logging with colors
        color_fn = self.color_map.get(mood, self.color_map["neutral"])
        log_message = f"[{datetime.now(timezone.utc).isoformat()}] ({mood.upper()}) {user_id}: {message_text}"
        media_info = f" [Media: {media.get('originalName', 'unknown')}]" if media else ""
        print(color_fn(log_message) + media_info)
        
        # Save chat data to temp log
        await self.save_chat_data({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "message_text": message_text,
            "mood": mood,
            "sentiment_score": score,
            "keywords": keywords,
            "reply_text": reply_text,
        })
        
        return {
            "user_id": user_id,
            "mood": mood,
            "sentiment_score": score,
            "keywords": keywords,
            "reply_text": reply_text.strip(),
            "crisis": mood == "crisis",
            "media": media,
            "follow_up_question": follow_up_question,
            "analysis_method": "VADER + keyword detection" if HAS_VADER else "keyword detection only",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # Additional Utility Methods
    async def get_conversation_insights(self, user_id: str) -> Dict[str, Any]:
        """Get deeper insights about the user's conversation patterns"""
        try:
            history = await self.get_chat_history(user_id)
            
            if not history:
                return {"insights": "No conversation data available"}
            
            moods = [entry.get('mood', 'neutral') for entry in history]
            keywords = []
            for entry in history:
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
            themes = self._identify_conversation_themes(keywords)
            
            return {
                "total_messages": len(history),
                "mood_distribution": mood_distribution,
                "dominant_mood": max(mood_distribution, key=mood_distribution.get),
                "mood_trend": mood_trend,
                "top_keywords": list(Counter(keywords).most_common(5)),
                "conversation_themes": themes,
                "needs_attention": mood_trend == "concerning",
                "session_length": "extended" if len(history) > 10 else "brief"
            }
        except Exception as e:
            print(f"Error getting conversation insights for {user_id}: {e}")
            return {"error": str(e)}
    
    def generate_personalized_greeting(self, chat_history: List[Dict[str, Any]]) -> str:
        """Generate a personalized greeting based on conversation history"""
        if not chat_history:
            return "Hello! I'm here to listen and support you."
        
        last_entry = chat_history[-1]
        last_mood = last_entry.get('mood', 'neutral')
        
        greetings = {
            'crisis': "I'm glad you're reaching out again. How are you feeling right now?",
            'sad': "Hello again. I hope you're feeling a bit better since we last talked.",
            'happy': "Hi there! I hope you're still feeling as positive as when we last spoke.",
            'anxious': "Hello! I hope some of that anxiety has settled since our last conversation.",
            'neutral': "Good to hear from you again. What's on your mind today?"
        }
        
        return greetings.get(last_mood, greetings['neutral'])
    
    async def track_progress_over_time(self, user_id: str) -> Dict[str, Any]:
        """Track user's emotional progress over time"""
        try:
            history = await self.get_chat_history(user_id)
            
            if len(history) < 3:
                return {"status": "insufficient_data", "message": "Need more conversation history to track progress"}
            
            # Sort by timestamp
            sorted_history = sorted(history, key=lambda x: x.get('timestamp', ''))
            
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
                "total_interactions": len(history)
            }
        except Exception as e:
            print(f"Error tracking progress for {user_id}: {e}")
            return {"error": str(e)}
    
    # Advanced Mood Detection
    def detect_emotional_intensity(self, text: str) -> Dict[str, Any]:
        """Detect the intensity of emotions in text"""
        if not text:
            return {"overall_intensity": "neutral", "intensity_breakdown": {}, "intensity_score": 0}
        
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
    
    def detect_mood_advanced(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Advanced mood detection combining VADER with additional analysis"""
        basic_result = self.detect_mood_offline(text)
        intensity_result = self.detect_emotional_intensity(text)
        
        return {
            **basic_result,
            "intensity": intensity_result,
            "analysis_method": "VADER + keyword detection" if HAS_VADER else "keyword detection only",
            "has_vader": HAS_VADER,
            "has_spacy": HAS_SPACY
        }
    
    async def run(self):
        """Run the MCP server"""
        print("🧠 Mental Health Support MCP Server Starting...")
        print(f"📁 Cache Directory: {self.CACHE_DIR}")
        print(f"📱 Contact Number: {self.MY_NUMBER}")
        print(f"🔍 VADER Available: {HAS_VADER}")
        print(f"🔤 SpaCy Available: {HAS_SPACY}")
        print(f"🎨 Colorama Available: {HAS_COLORAMA}")
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


# Additional Services (matching your original microservices)
class EmpathyService:
    """Standalone empathy service for generating adaptive replies"""
    
    @staticmethod
    def get_adaptive_reply(mood: str, score: float = 0.0) -> str:
        """Generate an empathetic reply based on detected mood and sentiment score"""
        # Implementation matches the main class method
        mcp_instance = MentalHealthMCP()
        return mcp_instance.get_adaptive_reply(mood, score)
    
    @staticmethod
    def get_contextual_response(mood: str, keywords: List[str], user_history: List[Dict] = None) -> str:
        """Generate a more contextual response based on mood, keywords, and user history"""
        base_response = EmpathyService.get_adaptive_reply(mood)
        
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


class MemorySummaryService:
    """Standalone memory summary service"""
    
    @staticmethod
    def summarize_chat(chat_history: List[Dict[str, Any]]) -> str:
        """Summarize the chat history to provide context for ongoing conversations"""
        mcp_instance = MentalHealthMCP()
        return mcp_instance.summarize_chat(chat_history)
    
    @staticmethod
    def get_conversation_insights(chat_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get deeper insights about the user's conversation patterns"""
        # Implementation using Counter and analysis logic
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
        
        return {
            "total_messages": len(chat_history),
            "mood_distribution": mood_distribution,
            "dominant_mood": max(mood_distribution, key=mood_distribution.get),
            "mood_trend": mood_trend,
            "top_keywords": list(Counter(keywords).most_common(5)),
            "needs_attention": mood_trend == "concerning",
            "session_length": "extended" if len(chat_history) > 10 else "brief"
        }


class OfflineCacheService:
    """Standalone offline cache service for data persistence"""
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path(__file__).parent.parent / "cache"
        self.user_data_dir = self.cache_dir / "users"
        self.global_cache_file = self.cache_dir / "global_chat_log.jsonl"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_user_file(self, user_id: str) -> Path:
        """Get the file path for a specific user's data"""
        hashed_id = hashlib.md5(user_id.encode()).hexdigest()
        return self.user_data_dir / f"user_{hashed_id}.json"
    
    async def save_chat(self, user_id: str, chat_entry: Dict[str, Any]) -> bool:
        """Save a chat entry for a specific user"""
        try:
            if "timestamp" not in chat_entry:
                chat_entry["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            # Load existing user data
            user_data = await self._load_user_data(user_id)
            user_data["chat_history"].append(chat_entry)
            
            # Update metadata
            if "metadata" not in user_data:
                user_data["metadata"] = {}
            
            user_data["metadata"].update({
                "total_messages": len(user_data["chat_history"]),
                "last_interaction": chat_entry["timestamp"],
                "last_mood": chat_entry.get("mood", "neutral")
            })
            
            # Save updated data
            success = await self._save_user_data(user_id, user_data)
            
            if success:
                await self._save_to_global_log(user_id, chat_entry)
            
            return success
        except Exception as e:
            print(f"Error in save_chat for user {user_id}: {e}")
            return False
    
    async def _load_user_data(self, user_id: str) -> Dict[str, Any]:
        """Load user data from file"""
        user_file = self._get_user_file(user_id)
        if user_file.exists():
            try:
                async with asyncio.to_thread(open, user_file, 'r', encoding='utf-8') as f:
                    content = await asyncio.to_thread(f.read)
                    return json.loads(content)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading user data for {user_id}: {e}")
        return {"user_id": user_id, "chat_history": [], "metadata": {}}
    
    async def _save_user_data(self, user_id: str, data: Dict[str, Any]) -> bool:
        """Save user data to file"""
        user_file = self._get_user_file(user_id)
        try:
            data["last_updated"] = datetime.now(timezone.utc).isoformat()
            async with asyncio.to_thread(open, user_file, 'w', encoding='utf-8') as f:
                await asyncio.to_thread(f.write, json.dumps(data, indent=2, ensure_ascii=False))
            return True
        except IOError as e:
            print(f"Error saving user data for {user_id}: {e}")
            return False
    
    async def _save_to_global_log(self, user_id: str, chat_entry: Dict[str, Any]):
        """Save chat entry to global log file"""
        try:
            global_entry = {
                "user_id_hash": hashlib.md5(user_id.encode()).hexdigest()[:8],
                **chat_entry
            }
            
            async with asyncio.to_thread(open, self.global_cache_file, 'a', encoding='utf-8') as f:
                await asyncio.to_thread(f.write, json.dumps(global_entry) + '\n')
        except Exception as e:
            print(f"Error saving to global log: {e}")
    
    async def get_chat_history(self, user_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get chat history for a specific user"""
        try:
            user_data = await self._load_user_data(user_id)
            history = user_data.get("chat_history", [])
            
            # Sort by timestamp
            history.sort(key=lambda x: x.get("timestamp", ""))
            
            if limit:
                return history[-limit:]
            
            return history
        except Exception as e:
            print(f"Error getting chat history for user {user_id}: {e}")
            return []


class MoodDetectionService:
    """Standalone mood detection service"""
    
    def __init__(self):
        self.crisis_keywords = [
            'suicide', 'kill myself', 'end my life', 'cant go on', "can't go on",
            'want to die', 'i will die', 'hurt myself', 'self harm', 'self-harm'
        ]
        
        self.emotion_keywords = {
            'sad': ['sad','depressed','lonely','hopeless','down','unhappy','tear','cry'],
            'anxious': ['anxious','nervous','worried','panic','panic attack','stressed','stress'],
            'angry': ['angry','mad','furious','annoyed','irritated','hate'],
            'happy': ['happy','great','good','glad','awesome','fine','joy','excited']
        }
    
    def detect_mood_offline(self, message: Optional[str]) -> Dict[str, Any]:
        """Main mood detection function"""
        if not message:
            return {'mood': 'neutral', 'score': 0}
        
        txt = message.lower()
        
        # Crisis detection
        if any(keyword in txt for keyword in self.crisis_keywords):
            return {'mood': 'crisis', 'score': None}
        
        # VADER sentiment scoring
        if HAS_VADER and sentiment_analyzer:
            s = sentiment_analyzer.polarity_scores(txt)
            score = int(s['compound'] * 5)
        else:
            score = self._simple_sentiment_score(txt)
        
        # Keyword detection
        for mood, keywords in self.emotion_keywords.items():
            if any(keyword in txt for keyword in keywords):
                return {'mood': mood, 'score': score}
        
        # Fallback thresholds
        if score <= -3:
            return {'mood': 'sad', 'score': score}
        if score <= -1:
            return {'mood': 'anxious', 'score': score}
        if score >= 3:
            return {'mood': 'happy', 'score': score}
        
        return {'mood': 'neutral', 'score': score}
    
    def _simple_sentiment_score(self, text: str) -> int:
        """Simple sentiment scoring fallback"""
        positive_words = ['good', 'great', 'awesome', 'happy', 'love', 'amazing', 'wonderful', 'excellent', 'fantastic', 'perfect']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'horrible', 'disgusting', 'worst', 'stupid', 'ugly', 'annoying']
        
        words = text.lower().split()
        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)
        
        if positive_count > negative_count:
            return min(5, positive_count * 2)
        elif negative_count > positive_count:
            return max(-5, -negative_count * 2)
        else:
            return 0


# Main execution
async def main():
    """Main function to run the MCP server"""
    mcp_server = MentalHealthMCP()
    await mcp_server.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)