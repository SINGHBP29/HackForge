#!/usr/bin/env python3
"""
Mental Health MCP Server - Streamlined Edition
==============================================
Features: AI Therapist + Crisis Prevention + Risk Assessment
"""

import json
import sys
import asyncio
import logging
import random
import hashlib
from typing import Dict, List, Any, Optional, Sequence, Tuple
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum
import sqlite3

# Core MCP imports
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

# Optional imports
try:
    from fastmcp import FastMCP
    HAS_FASTMCP = True
except ImportError:
    HAS_FASTMCP = False

try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False

try:
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    import joblib
    HAS_ML = True
except ImportError:
    HAS_ML = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MY_PHONE_NUMBER = "917047097971"
OLLAMA_MODEL = "llama3.2:1b"
CACHE_DIR = Path("mcp_cache")
DB_PATH = CACHE_DIR / "mental_health.db"
CACHE_DIR.mkdir(exist_ok=True)

# Crisis hotlines
EMERGENCY_CONTACTS = {
    "suicide_hotline": "988",
    "crisis_text": "741741",
    "local_emergency": "911",
    "india_helpline": "9152987821"
}

class RiskLevel(Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"

class InterventionType(Enum):
    SELF_HELP = "self_help"
    PEER_SUPPORT = "peer_support"
    PROFESSIONAL = "professional"
    EMERGENCY = "emergency"

@dataclass
class RiskAssessment:
    score: float
    level: RiskLevel
    factors: Dict[str, float]
    recommendations: List[str]
    intervention_type: InterventionType
    confidence: float

# Crisis patterns with weights
CRISIS_PATTERNS = {
    'immediate_danger': {
        'keywords': ['kill myself', 'end my life', 'suicide', 'want to die', 'going to hurt myself'],
        'weight': 1.0
    },
    'self_harm': {
        'keywords': ['cut myself', 'hurt myself', 'self harm', 'razor', 'pills'],
        'weight': 0.9
    },
    'despair': {
        'keywords': ['hopeless', 'no point', 'give up', 'cant go on', 'worthless'],
        'weight': 0.7
    },
    'planning': {
        'keywords': ['plan to', 'going to', 'tonight', 'tomorrow', 'method'],
        'weight': 0.8
    }
}

def init_database():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            risk_level TEXT DEFAULT 'low',
            total_sessions INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            message TEXT,
            mood TEXT,
            risk_score REAL,
            intervention_triggered BOOLEAN DEFAULT FALSE,
            response TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crisis_interventions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            risk_score REAL,
            intervention_type TEXT,
            bot_response TEXT,
            follow_up_required BOOLEAN DEFAULT TRUE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS therapy_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            goal_text TEXT,
            category TEXT,
            target_date DATE,
            progress_percentage REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    conn.commit()
    conn.close()

class RiskPredictor:
    def __init__(self):
        self.model = None
        self.features = ['avg_sentiment_7d', 'mood_stability', 'session_frequency', 'crisis_keyword_count']
        self.load_or_create_model()
    
    def load_or_create_model(self):
        """Load existing model or create a new one"""
        model_path = CACHE_DIR / "risk_model.joblib"
        if model_path.exists() and HAS_ML:
            try:
                self.model = joblib.load(model_path)
            except:
                self.create_default_model()
        else:
            self.create_default_model()
    
    def create_default_model(self):
        """Create a simple risk prediction model"""
        if not HAS_ML:
            return
        
        np.random.seed(42)
        n_samples = 1000
        X = np.random.rand(n_samples, len(self.features))
        
        # Create realistic risk patterns
        risk_scores = []
        for i in range(n_samples):
            score = X[i][0] * 0.3 + (1 - X[i][1]) * 0.25 + X[i][3] * 0.4 + (1 - X[i][2]) * 0.15
            risk_scores.append(min(1.0, score))
        
        y = (np.array(risk_scores) > 0.6).astype(int)
        self.model = LogisticRegression()
        self.model.fit(X, y)
        joblib.dump(self.model, CACHE_DIR / "risk_model.joblib")
    
    def extract_features(self, user_id: str) -> np.ndarray:
        """Extract features for risk prediction"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT mood, risk_score, timestamp, message 
            FROM interactions 
            WHERE user_id = ? 
            ORDER BY timestamp DESC LIMIT 20
        ''', (user_id,))
        
        interactions = cursor.fetchall()
        conn.close()
        
        if not interactions:
            return np.array([0.5] * len(self.features))
        
        features = []
        
        # Average sentiment
        recent_scores = [r[1] for r in interactions if r[1] is not None]
        features.append(np.mean(recent_scores) if recent_scores else 0.5)
        
        # Mood stability
        moods = [r[0] for r in interactions]
        mood_scores = {'happy': 1.0, 'neutral': 0.5, 'sad': 0.2, 'anxious': 0.3, 'angry': 0.1}
        mood_values = [mood_scores.get(m, 0.5) for m in moods]
        features.append(1.0 - np.var(mood_values) if len(mood_values) > 1 else 0.5)
        
        # Session frequency
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        recent_sessions = [i for i in interactions if datetime.fromisoformat(i[2].replace('Z', '+00:00')) > week_ago]
        features.append(min(1.0, len(recent_sessions) / 7))
        
        # Crisis keyword count
        crisis_count = 0
        for interaction in interactions[:10]:
            message = interaction[3].lower()
            for pattern in CRISIS_PATTERNS.values():
                crisis_count += sum(1 for keyword in pattern['keywords'] if keyword in message)
        features.append(min(1.0, crisis_count / 10))
        
        return np.array(features)
    
    def predict_risk(self, user_id: str) -> RiskAssessment:
        """Predict mental health risk"""
        features = self.extract_features(user_id)
        
        if self.model and HAS_ML:
            risk_prob = self.model.predict_proba(features.reshape(1, -1))[0][1]
        else:
            risk_prob = np.mean(features)
        
        # Determine risk level
        if risk_prob >= 0.8:
            risk_level = RiskLevel.CRITICAL
            intervention = InterventionType.EMERGENCY
        elif risk_prob >= 0.6:
            risk_level = RiskLevel.HIGH
            intervention = InterventionType.PROFESSIONAL
        elif risk_prob >= 0.4:
            risk_level = RiskLevel.MODERATE
            intervention = InterventionType.PEER_SUPPORT
        else:
            risk_level = RiskLevel.LOW
            intervention = InterventionType.SELF_HELP
        
        recommendations = self.generate_recommendations(risk_level)
        
        return RiskAssessment(
            score=risk_prob,
            level=risk_level,
            factors={f: float(v) for f, v in zip(self.features, features)},
            recommendations=recommendations,
            intervention_type=intervention,
            confidence=0.8
        )
    
    def generate_recommendations(self, risk_level: RiskLevel) -> List[str]:
        """Generate personalized recommendations"""
        if risk_level == RiskLevel.CRITICAL:
            return [
                "Immediate professional intervention required",
                "Contact emergency services or crisis hotline",
                "Consider inpatient care evaluation"
            ]
        elif risk_level == RiskLevel.HIGH:
            return [
                "Schedule urgent appointment with mental health professional",
                "Increase session frequency to daily check-ins",
                "Consider medication evaluation"
            ]
        elif risk_level == RiskLevel.MODERATE:
            return [
                "Regular therapy sessions recommended",
                "Practice daily mindfulness or meditation",
                "Engage with peer support groups"
            ]
        else:
            return [
                "Continue self-care practices",
                "Weekly mental health check-ins",
                "Maintain social connections"
            ]

class CrisisManager:
    def __init__(self):
        self.risk_predictor = RiskPredictor()
    
    async def assess_crisis_level(self, message: str, user_id: str) -> Tuple[float, bool]:
        """Assess crisis level from message and context"""
        crisis_score = 0.0
        immediate_crisis = False
        
        message_lower = message.lower()
        
        # Check for crisis patterns
        for pattern_name, pattern in CRISIS_PATTERNS.items():
            for keyword in pattern['keywords']:
                if keyword in message_lower:
                    crisis_score += pattern['weight']
                    if pattern['weight'] >= 0.9:
                        immediate_crisis = True
        
        # Contextual risk assessment
        risk_assessment = self.risk_predictor.predict_risk(user_id)
        
        # Combine scores
        final_score = min(1.0, (crisis_score * 0.6) + (risk_assessment.score * 0.4))
        
        return final_score, immediate_crisis or final_score >= 0.8
    
    async def trigger_crisis_intervention(self, user_id: str, message: str, crisis_score: float):
        """Trigger bot-based crisis intervention"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        bot_response = self.generate_crisis_response()
        
        # Log crisis event
        cursor.execute('''
            INSERT INTO crisis_interventions 
            (user_id, risk_score, intervention_type, bot_response)
            VALUES (?, ?, ?, ?)
        ''', (user_id, crisis_score, 'emergency', bot_response))
        
        conn.commit()
        conn.close()
        
        logger.critical(f"CRISIS INTERVENTION triggered for user {user_id}: score {crisis_score}")
        
        return bot_response
    
    def generate_crisis_response(self) -> str:
        """Generate bot crisis response"""
        return """🚨 **IMMEDIATE SAFETY ALERT** 🚨

I'm very concerned about what you've shared. Your safety is my top priority right now.

**GET HELP NOW:**
• **Crisis Lifeline:** 988 (24/7 support)
• **Crisis Text:** Text HOME to 741741
• **Emergency:** 911

**You are NOT alone:**
- Professional counselors are available 24/7
- Your life has value and meaning
- This pain you're feeling can be treated
- There are people who care about you

Please reach out for help right now. These feelings can change with proper support."""

async def enhanced_llm_analyze(message: str, user_context: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Enhanced LLM analysis with risk prediction"""
    
    crisis_manager = CrisisManager()
    
    # Crisis assessment first
    crisis_score, immediate_crisis = await crisis_manager.assess_crisis_level(message, user_id)
    
    if immediate_crisis:
        # Trigger crisis intervention
        bot_response = await crisis_manager.trigger_crisis_intervention(user_id, message, crisis_score)
        
        return {
            "mood": "crisis",
            "confidence": 0.95,
            "crisis_detected": True,
            "crisis_score": crisis_score,
            "intervention_triggered": True,
            "response": bot_response
        }
    
    # Regular analysis
    if not HAS_OLLAMA:
        return await fallback_enhanced_response(message, user_context, user_id)
    
    try:
        # Get risk assessment
        risk_predictor = RiskPredictor()
        risk_assessment = risk_predictor.predict_risk(user_id)
        
        # Build conversation context
        conversation_history = ""
        if not user_context["is_new_user"]:
            conversation_history = f"Previous conversation: {user_context['recent_summary']}\n"
            conversation_history += f"Risk level: {risk_assessment.level.value} ({risk_assessment.score:.2f})\n"
        
        # LLM prompt with risk awareness
        analysis_prompt = f"""You are an AI therapist with risk assessment capabilities.

{conversation_history}

Current message: "{message}"
Risk factors: {risk_assessment.factors}

Respond with JSON:
{{
    "mood": "sad/anxious/angry/happy/tired/confused/neutral",
    "confidence": 0.0-1.0,
    "key_emotions": ["list", "emotions"],
    "therapy_insights": ["professional", "observations"],
    "response": "Warm, professional response (under 200 words)"
}}"""

        # Call Ollama
        ollama_response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: ollama.generate(model=OLLAMA_MODEL, prompt=analysis_prompt)
        )
        
        llm_text = ollama_response['response'].strip()
        
        if '{' in llm_text and '}' in llm_text:
            json_start = llm_text.find('{')
            json_end = llm_text.rfind('}') + 1
            json_text = llm_text[json_start:json_end]
            result = json.loads(json_text)
            
            # Add risk assessment to response
            result["risk_assessment"] = {
                "score": risk_assessment.score,
                "level": risk_assessment.level.value,
                "recommendations": risk_assessment.recommendations
            }
            result["crisis_detected"] = False
            result["llm_generated"] = True
            
            return result
        
    except Exception as e:
        logger.error(f"LLM analysis failed: {e}")
    
    return await fallback_enhanced_response(message, user_context, user_id)

async def fallback_enhanced_response(message: str, user_context: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Enhanced fallback response"""
    mood = basic_mood_detection(message)
    
    # Get risk assessment
    risk_predictor = RiskPredictor()
    risk_assessment = risk_predictor.predict_risk(user_id)
    
    # Build response
    response = "I'm here to support you. "
    
    if risk_assessment.level != RiskLevel.LOW:
        response += f"I notice some concerning patterns and want to make sure you're getting the support you need. "
    
    if not user_context["is_new_user"]:
        response += f"I remember our previous conversations where you were feeling {user_context['last_mood']}. "
    
    # Mood-specific response
    mood_responses = {
        "sad": "I can sense the sadness in your words. What's weighing most heavily on your heart right now?",
        "anxious": "I hear the worry in what you're sharing. What thoughts are making you feel most anxious?",
        "happy": "It's wonderful to hear some positivity from you! What's bringing you joy?",
        "angry": "I can feel your frustration. What's triggering these angry feelings?",
        "tired": "You sound emotionally exhausted. What's been draining your energy?",
        "neutral": "How are you feeling today? What's on your mind?"
    }
    
    response += mood_responses.get(mood, "What would you like to explore together?")
    
    return {
        "mood": mood,
        "confidence": 0.6,
        "crisis_detected": False,
        "risk_assessment": {
            "score": risk_assessment.score,
            "level": risk_assessment.level.value,
            "recommendations": risk_assessment.recommendations
        },
        "response": response,
        "llm_generated": False
    }

def basic_mood_detection(message: str) -> str:
    """Basic mood detection"""
    message_lower = message.lower()
    
    # Crisis patterns (highest priority)
    for pattern in CRISIS_PATTERNS.values():
        if any(keyword in message_lower for keyword in pattern['keywords']):
            return "crisis"
    
    # Emotion detection
    emotion_patterns = {
        'sad': ['sad', 'depressed', 'down', 'miserable', 'heartbroken'],
        'anxious': ['anxious', 'nervous', 'worried', 'panic', 'stress'],
        'angry': ['angry', 'mad', 'furious', 'rage', 'irritated'],
        'happy': ['happy', 'joy', 'excited', 'great', 'wonderful'],
        'tired': ['tired', 'exhausted', 'drained', 'weary', 'fatigue'],
        'confused': ['confused', 'lost', 'uncertain', 'unclear']
    }
    
    # Score each emotion
    emotion_scores = {}
    for emotion, keywords in emotion_patterns.items():
        score = sum(1 for keyword in keywords if keyword in message_lower)
        if score > 0:
            emotion_scores[emotion] = score
    
    if emotion_scores:
        return max(emotion_scores.items(), key=lambda x: x[1])[0]
    
    return "neutral"

def get_user_context(user_id: str) -> Dict[str, Any]:
    """Get user context from database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user_info = cursor.fetchone()
        
        cursor.execute('''
            SELECT timestamp, mood, risk_score, message 
            FROM interactions 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 10
        ''', (user_id,))
        
        interactions = cursor.fetchall()
        conn.close()
        
        if not user_info and not interactions:
            return {"is_new_user": True, "conversation_count": 0, "recent_summary": ""}
        
        mood_pattern = [i[1] for i in interactions if i[1]]
        recent_summary = ""
        
        if len(interactions) >= 2:
            last_3 = interactions[:3]
            summary_parts = []
            for interaction in last_3:
                mood = interaction[1] or "neutral"
                msg_preview = interaction[3][:50] + "..." if len(interaction[3]) > 50 else interaction[3]
                summary_parts.append(f"User was {mood}: '{msg_preview}'")
            recent_summary = " | ".join(summary_parts)
        
        return {
            "is_new_user": len(interactions) == 0,
            "conversation_count": len(interactions),
            "last_mood": interactions[0][1] if interactions and interactions[0][1] else "neutral",
            "recent_summary": recent_summary,
            "mood_pattern": mood_pattern[:5]
        }
        
    except Exception as e:
        logger.error(f"Error getting user context: {e}")
        return {"is_new_user": True, "conversation_count": 0, "recent_summary": ""}

class GoalsManager:
    def create_goal(self, user_id: str, goal_text: str, category: str, target_date: str) -> bool:
        """Create a new therapy goal"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO therapy_goals (user_id, goal_text, category, target_date)
                VALUES (?, ?, ?, ?)
            ''', (user_id, goal_text, category, target_date))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to create goal: {e}")
            return False
    
    def get_user_goals(self, user_id: str) -> List[Dict]:
        """Get all goals for a user"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, goal_text, category, target_date, progress_percentage, status
                FROM therapy_goals
                WHERE user_id = ? AND status = 'active'
                ORDER BY created_at DESC
            ''', (user_id,))
            
            goals = []
            for row in cursor.fetchall():
                goals.append({
                    'id': row[0], 'goal_text': row[1], 'category': row[2],
                    'target_date': row[3], 'progress_percentage': row[4], 'status': row[5]
                })
            
            conn.close()
            return goals
        except Exception as e:
            logger.error(f"Failed to get user goals: {e}")
            return []

# MCP Server
class MentalHealthServer:
    def __init__(self):
        self.server = Server("mental-health-ai")
        self.crisis_manager = CrisisManager()
        self.goals_manager = GoalsManager()
        init_database()
        self._setup_tools()
    
    def _setup_tools(self):
        @self.server.list_tools()
        async def list_tools() -> List[types.Tool]:
            return [
                types.Tool(
                    name="chat_with_ai_therapist",
                    description="AI therapist with crisis prevention and risk assessment",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string"},
                            "message": {"type": "string"}
                        },
                        "required": ["user_id", "message"]
                    }
                ),
                types.Tool(
                    name="get_risk_assessment",
                    description="Get current mental health risk assessment",
                    inputSchema={
                        "type": "object",
                        "properties": {"user_id": {"type": "string"}},
                        "required": ["user_id"]
                    }
                ),
                types.Tool(
                    name="create_therapy_goal",
                    description="Create personalized therapy goal",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string"},
                            "goal_text": {"type": "string"},
                            "category": {"type": "string"}
                        },
                        "required": ["user_id", "goal_text", "category"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> Sequence[types.TextContent]:
            try:
                if name == "chat_with_ai_therapist":
                    return await self._handle_chat(arguments)
                elif name == "get_risk_assessment":
                    return await self._handle_risk_assessment(arguments)
                elif name == "create_therapy_goal":
                    return await self._handle_create_goal(arguments)
                else:
                    return [types.TextContent(type="text", text=json.dumps({"error": "Unknown tool"}))]
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                return [types.TextContent(type="text", text=json.dumps({"error": str(e)}))]
    
    async def _handle_chat(self, arguments: dict) -> Sequence[types.TextContent]:
        user_id = arguments.get("user_id", "unknown")
        message = arguments.get("message", "")
        
        # Get user context and analyze
        user_context = get_user_context(user_id)
        analysis = await enhanced_llm_analyze(message, user_context, user_id)
        response = analysis["response"]
        
        # Save interaction
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO interactions (user_id, message, mood, risk_score, response)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, message, analysis.get("mood"), 
              analysis.get("risk_assessment", {}).get("score"), response))
        conn.commit()
        conn.close()
        
        result = {
            "success": True,
            "analysis": analysis,
            "response": response,
            "crisis_prevention": analysis.get("crisis_detected", False),
            "risk_level": analysis.get("risk_assessment", {}).get("level", "low")
        }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _handle_risk_assessment(self, arguments: dict) -> Sequence[types.TextContent]:
        user_id = arguments.get("user_id")
        risk_predictor = RiskPredictor()
        assessment = risk_predictor.predict_risk(user_id)
        
        result = {
            "risk_score": assessment.score,
            "risk_level": assessment.level.value,
            "confidence": assessment.confidence,
            "recommendations": assessment.recommendations
        }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _handle_create_goal(self, arguments: dict) -> Sequence[types.TextContent]:
        user_id = arguments.get("user_id")
        goal_text = arguments.get("goal_text")
        category = arguments.get("category")
        target_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        success = self.goals_manager.create_goal(user_id, goal_text, category, target_date)
        
        result = {
            "success": success,
            "message": "Therapy goal created successfully!" if success else "Failed to create goal"
        }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def run_stdio(self):
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, self.server.create_initialization_options())

# FastMCP for Puch AI
def create_fastmcp_server():
    if not HAS_FASTMCP:
        raise ImportError("FastMCP not available")
    
    mcp = FastMCP("AI Mental Health Therapist")
    crisis_manager = CrisisManager()
    goals_manager = GoalsManager()
    init_database()
    
    @mcp.tool()
    def validate() -> str:
        """Validation for Puch AI"""
        return MY_PHONE_NUMBER
    
    @mcp.tool()
    async def therapy_chat(user_id: str, message: str) -> str:
        """AI therapy chat with crisis prevention"""
        try:
            user_context = get_user_context(user_id)
            analysis = await enhanced_llm_analyze(message, user_context, user_id)
            response = analysis["response"]
            
            # Store interaction
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
            cursor.execute('''
                INSERT INTO interactions (user_id, message, mood, risk_score, response)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, message, analysis.get("mood"), 
                  analysis.get("risk_assessment", {}).get("score"), response))
            conn.commit()
            conn.close()
            
            # Enhanced response with recommendations
            if not analysis.get("crisis_detected", False):
                mood = analysis.get("mood", "neutral")
                if mood == "sad":
                    response += "\n\n💡 **Try this:** Take a warm bath or call a trusted friend"
                elif mood == "anxious":
                    response += "\n\n💡 **Try this:** Practice 4-7-8 breathing (inhale 4, hold 7, exhale 8)"
                elif mood == "happy":
                    response += "\n\n💡 **Try this:** Share your joy with someone you care about"
            
            return json.dumps({
                "success": True,
                "response": response,
                "mood_detected": analysis.get("mood"),
                "crisis_prevented": analysis.get("crisis_detected", False),
                "risk_level": analysis.get("risk_assessment", {}).get("level", "low"),
                "remembers_you": not user_context["is_new_user"]
            })
            
        except Exception as e:
            logger.error(f"Therapy chat failed: {e}")
            return json.dumps({
                "success": False, 
                "error": str(e),
                "fallback_message": "I'm here to help. How are you feeling right now?"
            })
    
    @mcp.tool()
    def set_goal(user_id: str, goal_text: str, category: str) -> str:
        """Set new therapy goal"""
        try:
            target_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            success = goals_manager.create_goal(user_id, goal_text, category, target_date)
            
            return json.dumps({
                "success": success,
                "goal_created": goal_text if success else None,
                "target_date": target_date,
                "message": "Your therapy goal has been set! We'll track your progress together." if success else "Failed to create goal"
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    @mcp.tool()
    async def crisis_check(user_id: str, message: str) -> str:
        """Dedicated crisis assessment"""
        try:
            crisis_score, immediate_crisis = await crisis_manager.assess_crisis_level(message, user_id)
            
            if immediate_crisis:
                bot_response = await crisis_manager.trigger_crisis_intervention(user_id, message, crisis_score)
                return json.dumps({
                    "crisis_detected": True,
                    "crisis_score": crisis_score,
                    "intervention_triggered": True,
                    "bot_response": bot_response,
                    "immediate_actions": [
                        "Call 988 (Suicide Prevention Lifeline)",
                        "Text HOME to 741741 (Crisis Text Line)",
                        "Contact emergency services: 911"
                    ]
                })
            else:
                return json.dumps({
                    "crisis_detected": False,
                    "crisis_score": crisis_score,
                    "status": "Monitoring - no immediate intervention needed"
                })
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    @mcp.tool()
    def get_user_progress(user_id: str) -> str:
        """Get user's therapy progress"""
        try:
            goals = goals_manager.get_user_goals(user_id)
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*), AVG(risk_score) 
                FROM interactions 
                WHERE user_id = ? AND timestamp > datetime('now', '-30 days')
            ''', (user_id,))
            stats = cursor.fetchone()
            conn.close()
            
            return json.dumps({
                "active_goals": len(goals),
                "goals": goals[:3],  # Top 3 goals
                "sessions_last_30_days": stats[0] if stats else 0,
                "average_risk_score": round(stats[1], 2) if stats and stats[1] else 0,
                "progress_summary": f"You've had {stats[0]} sessions this month with good progress on your goals." if stats else "Start your mental health journey today!"
            })
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    return mcp

# Main execution
async def main():
    print("🚀 Mental Health MCP Server - Streamlined Edition")
    print("=" * 50)
    
    # Check dependencies
    if not HAS_OLLAMA:
        print("⚠️  Ollama not found! Install for advanced LLM features:")
        print("   curl -fsSL https://ollama.ai/install.sh | sh")
        print("   ollama pull llama3.2:1b")
    else:
        print(f"✅ Ollama LLM ready: {OLLAMA_MODEL}")
    
    if not HAS_ML:
        print("⚠️  ML libraries missing! Install: pip install scikit-learn numpy")
    else:
        print("✅ Machine Learning risk prediction ready")
    
    print("\n🧠 **CORE FEATURES ACTIVE:**")
    print("   • AI Therapist with conversational memory")
    print("   • Real-time crisis prevention via bot notifications")
    print("   • Risk prediction & assessment")
    print("   • Therapy goal setting and tracking")
    print("   • No external notifications (email/SMS removed)")
    
    # Initialize database
    init_database()
    print("✅ Database initialized")
    
    if len(sys.argv) < 2:
        print("\n🔧 Starting MCP stdio server...")
        server = MentalHealthServer()
        await server.run_stdio()
        return
    
    mode = sys.argv[1].lower()
    
    if mode in ["stdio", "mcp"]:
        print(f"\n🔧 Starting MCP server in {mode} mode...")
        server = MentalHealthServer()
        await server.run_stdio()
    
    elif mode == "puch":
        if not HAS_FASTMCP:
            print("❌ FastMCP not installed. Run: pip install fastmcp")
            return
        
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8085
        print(f"\n🤖 AI Mental Health Therapist starting on port {port}...")
        print(f"📞 Validation Phone: {MY_PHONE_NUMBER}")
        print("🌟 **STREAMLINED FEATURES ACTIVE**")
        
        mcp_server = create_fastmcp_server()
        await mcp_server.run_async(transport="streamable-http", host="0.0.0.0", port=port)
    
    else:
        print("Usage:")
        print("  python mental_health_mcp.py              # MCP stdio")
        print("  python mental_health_mcp.py puch 8085    # Puch AI server")
        print("  python mental_health_mcp.py mcp          # MCP protocol server")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Mental Health AI shutting down safely...")
    except Exception as e:
        logger.error(f"Critical error: {e}")
        sys.exit(1)