"""
Offline Cache Service - Handles local storage of chat data and user sessions
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import hashlib

# Create cache directory
CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

USER_DATA_DIR = CACHE_DIR / "users"
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

GLOBAL_CACHE_FILE = CACHE_DIR / "global_chat_log.jsonl"

def _get_user_file(user_id: str) -> Path:
    """Get the file path for a specific user's data"""
    # Hash user_id for privacy and filename safety
    hashed_id = hashlib.md5(user_id.encode()).hexdigest()
    return USER_DATA_DIR / f"user_{hashed_id}.json"

def _load_user_data(user_id: str) -> Dict[str, Any]:
    """Load user data from file"""
    user_file = _get_user_file(user_id)
    if user_file.exists():
        try:
            with open(user_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading user data for {user_id}: {e}")
            return {"user_id": user_id, "chat_history": [], "metadata": {}}
    return {"user_id": user_id, "chat_history": [], "metadata": {}}

def _save_user_data(user_id: str, data: Dict[str, Any]) -> bool:
    """Save user data to file"""
    user_file = _get_user_file(user_id)
    try:
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"Error saving user data for {user_id}: {e}")
        return False

async def saveChat(user_id: str, chat_entry: Dict[str, Any]) -> bool:
    """
    Save a chat entry for a specific user
    
    Args:
        user_id: Unique identifier for the user
        chat_entry: Dictionary containing chat data
    
    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        # Ensure timestamp is present
        if "timestamp" not in chat_entry:
            chat_entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # Load existing user data
        user_data = _load_user_data(user_id)
        
        # Add new chat entry
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
        success = _save_user_data(user_id, user_data)
        
        # Also save to global log
        if success:
            await _save_to_global_log(user_id, chat_entry)
        
        return success
        
    except Exception as e:
        print(f"Error in saveChat for user {user_id}: {e}")
        return False

async def _save_to_global_log(user_id: str, chat_entry: Dict[str, Any]):
    """Save chat entry to global log file"""
    try:
        global_entry = {
            "user_id_hash": hashlib.md5(user_id.encode()).hexdigest()[:8],  # Partial hash for privacy
            **chat_entry
        }
        
        with open(GLOBAL_CACHE_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(global_entry) + '\n')
            
    except Exception as e:
        print(f"Error saving to global log: {e}")

def getChatHistory(user_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get chat history for a specific user
    
    Args:
        user_id: Unique identifier for the user
        limit: Maximum number of entries to return (most recent first)
    
    Returns:
        List of chat entries, sorted by timestamp (oldest first)
    """
    try:
        user_data = _load_user_data(user_id)
        history = user_data.get("chat_history", [])
        
        # Sort by timestamp
        sorted_history = sorted(history, key=lambda x: x.get("timestamp", ""))
        
        if limit:
            return sorted_history[-limit:]  # Return most recent entries
        
        return sorted_history
        
    except Exception as e:
        print(f"Error getting chat history for user {user_id}: {e}")
        return []

def getUserMetadata(user_id: str) -> Dict[str, Any]:
    """
    Get metadata for a specific user
    
    Args:
        user_id: Unique identifier for the user
    
    Returns:
        Dictionary containing user metadata
    """
    try:
        user_data = _load_user_data(user_id)
        metadata = user_data.get("metadata", {})
        
        # Calculate additional stats
        history = user_data.get("chat_history", [])
        if history:
            moods = [entry.get("mood", "neutral") for entry in history]
            from collections import Counter
            mood_counts = Counter(moods)
            
            metadata.update({
                "dominant_mood": mood_counts.most_common(1)[0][0] if mood_counts else "neutral",
                "mood_distribution": dict(mood_counts),
                "first_interaction": history[0].get("timestamp") if history else None,
                "conversation_span_days": _calculate_conversation_span(history)
            })
        
        return metadata
        
    except Exception as e:
        print(f"Error getting metadata for user {user_id}: {e}")
        return {}

def _calculate_conversation_span(history: List[Dict[str, Any]]) -> Optional[int]:
    """Calculate the span of conversation in days"""
    if len(history) < 2:
        return 0
    
    try:
        timestamps = [entry.get("timestamp") for entry in history if entry.get("timestamp")]
        if len(timestamps) < 2:
            return 0
        
        first_time = datetime.fromisoformat(timestamps[0].replace('Z', '+00:00'))
        last_time = datetime.fromisoformat(timestamps[-1].replace('Z', '+00:00'))
        
        return (last_time - first_time).days
        
    except Exception:
        return None

def clearUserData(user_id: str) -> bool:
    """
    Clear all data for a specific user
    
    Args:
        user_id: Unique identifier for the user
    
    Returns:
        bool: True if cleared successfully
    """
    try:
        user_file = _get_user_file(user_id)
        if user_file.exists():
            user_file.unlink()
            return True
        return True  # File didn't exist, consider it cleared
        
    except Exception as e:
        print(f"Error clearing data for user {user_id}: {e}")
        return False

def getAllUsers() -> List[str]:
    """
    Get list of all users with stored data
    Note: Returns hashed user IDs for privacy
    
    Returns:
        List of hashed user IDs
    """
    try:
        user_files = list(USER_DATA_DIR.glob("user_*.json"))
        return [f.stem.replace("user_", "") for f in user_files]
        
    except Exception as e:
        print(f"Error getting user list: {e}")
        return []

def exportUserData(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Export all data for a user (for data portability)
    
    Args:
        user_id: Unique identifier for the user
    
    Returns:
        Complete user data or None if error
    """
    try:
        return _load_user_data(user_id)
    except Exception as e:
        print(f"Error exporting data for user {user_id}: {e}")
        return None

def getCacheStats() -> Dict[str, Any]:
    """
    Get statistics about the cache
    
    Returns:
        Dictionary with cache statistics
    """
    try:
        stats = {
            "total_users": len(getAllUsers()),
            "cache_directory": str(CACHE_DIR),
            "global_log_size": 0
        }
        
        if GLOBAL_CACHE_FILE.exists():
            stats["global_log_size"] = GLOBAL_CACHE_FILE.stat().st_size
            
            # Count total entries in global log
            with open(GLOBAL_CACHE_FILE, 'r', encoding='utf-8') as f:
                stats["total_global_entries"] = sum(1 for _ in f)
        
        return stats
        
    except Exception as e:
        print(f"Error getting cache stats: {e}")
        return {"error": str(e)}

# Batch operations
async def saveBatchChats(batch_data: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Save multiple chat entries in batch
    
    Args:
        batch_data: List of dictionaries, each containing user_id and chat_entry
    
    Returns:
        Dictionary with success/failure counts
    """
    results = {"success": 0, "failed": 0}
    
    for item in batch_data:
        user_id = item.get("user_id")
        chat_entry = item.get("chat_entry")
        
        if user_id and chat_entry:
            success = await saveChat(user_id, chat_entry)
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1
        else:
            results["failed"] += 1
    
    return results