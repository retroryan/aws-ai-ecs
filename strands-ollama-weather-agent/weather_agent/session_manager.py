"""
Session Management for Weather Agent API

This module provides session management capabilities for stateful conversations.
Phase 1 implementation focuses on core functionality with in-memory storage.
"""

import uuid
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class SessionData:
    """Data structure for a conversation session."""
    session_id: str
    created_at: datetime
    last_activity: datetime
    expires_at: Optional[datetime]
    conversation_turns: int = 0
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    storage_type: str = "memory"


class SessionManager:
    """
    Manages conversation sessions for the Weather Agent API.
    
    Phase 1: In-memory storage with basic TTL support.
    """
    
    def __init__(self, default_ttl_minutes: int = 60, storage_dir: Optional[str] = None):
        """
        Initialize the session manager.
        
        Args:
            default_ttl_minutes: Default session TTL in minutes
            storage_dir: Directory for file-based storage (Phase 2)
        """
        self.sessions: Dict[str, SessionData] = {}
        self.default_ttl_minutes = default_ttl_minutes
        self.storage_dir = storage_dir  # For future phases
        self._lock = asyncio.Lock()
        
        logger.info(f"SessionManager initialized with {default_ttl_minutes} minute TTL")
    
    async def create_session(
        self,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ttl_minutes: Optional[int] = None
    ) -> SessionData:
        """
        Create a new session.
        
        Args:
            user_id: Optional user identifier
            metadata: Optional session metadata
            ttl_minutes: Session TTL in minutes (overrides default)
            
        Returns:
            Newly created SessionData
        """
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        ttl = ttl_minutes or self.default_ttl_minutes
        
        session = SessionData(
            session_id=session_id,
            created_at=now,
            last_activity=now,
            expires_at=now + timedelta(minutes=ttl) if ttl > 0 else None,
            user_id=user_id,
            metadata=metadata or {},
            storage_type="memory"
        )
        
        async with self._lock:
            self.sessions[session_id] = session
        
        logger.info(f"Created session {session_id} for user {user_id}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        Get a session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionData if found and not expired, None otherwise
        """
        async with self._lock:
            session = self.sessions.get(session_id)
            
            if not session:
                return None
            
            # Check if expired
            if session.expires_at and datetime.utcnow() > session.expires_at:
                # Remove expired session
                del self.sessions[session_id]
                logger.info(f"Session {session_id} has expired")
                return None
            
            return session
    
    async def update_activity(self, session_id: str) -> bool:
        """
        Update the last activity timestamp for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was updated, False if not found
        """
        async with self._lock:
            session = self.sessions.get(session_id)
            if session:
                session.last_activity = datetime.utcnow()
                session.conversation_turns += 1
                return True
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was deleted, False if not found
        """
        async with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.info(f"Deleted session {session_id}")
                return True
            return False
    
    async def get_session_count(self) -> int:
        """Get the current number of active sessions."""
        async with self._lock:
            # Remove expired sessions during count
            now = datetime.utcnow()
            expired = [
                sid for sid, session in self.sessions.items()
                if session.expires_at and now > session.expires_at
            ]
            for sid in expired:
                del self.sessions[sid]
            
            return len(self.sessions)
    
    def get_session_info(self, session: SessionData) -> Dict[str, Any]:
        """
        Get session information in a serializable format.
        
        Args:
            session: SessionData object
            
        Returns:
            Dictionary with session information
        """
        return {
            'session_id': session.session_id,
            'created_at': session.created_at.isoformat(),
            'last_activity': session.last_activity.isoformat(),
            'expires_at': session.expires_at.isoformat() if session.expires_at else None,
            'conversation_turns': session.conversation_turns,
            'user_id': session.user_id,
            'metadata': session.metadata,
            'storage_type': session.storage_type,
            'time_remaining_seconds': int((session.expires_at - datetime.utcnow()).total_seconds()) 
                if session.expires_at and session.expires_at > datetime.utcnow() else 0
        }