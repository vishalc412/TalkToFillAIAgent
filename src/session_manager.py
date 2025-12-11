"""
Session and state management for form-filling conversations.
"""

from typing import Dict, Optional
import json
import uuid
from datetime import datetime, timedelta
import logging

from src.models import FormSchema, FormState, ConversationState
from src.config import Settings

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages conversation sessions and state.
    In production, this would use Redis or a database.
    For now, using in-memory storage.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.sessions: Dict[str, ConversationState] = {}
        self.form_schemas: Dict[str, FormSchema] = {}

    def create_session(
        self, form_schema: FormSchema, session_id: Optional[str] = None
    ) -> str:
        """
        Create a new conversation session.

        Args:
            form_schema: The form schema for this session
            session_id: Optional session ID (will generate if not provided)

        Returns:
            Session ID
        """
        if session_id is None:
            session_id = str(uuid.uuid4())

        # Initialize form state
        form_state = FormState(
            form_id=form_schema.form_id,
            session_id=session_id,
        )

        # Create conversation state
        conversation_state = ConversationState(
            session_id=session_id,
            form_state=form_state,
        )

        # Store session
        self.sessions[session_id] = conversation_state
        self.form_schemas[session_id] = form_schema

        # Add initial system message
        conversation_state.add_message(
            "assistant",
            self._generate_welcome_message(form_schema),
        )

        logger.info(f"Created session {session_id} for form {form_schema.form_id}")

        return session_id

    def get_session(self, session_id: str) -> Optional[ConversationState]:
        """Get conversation state for a session."""
        # Check if session exists and is not expired
        if session_id in self.sessions:
            session = self.sessions[session_id]

            # Check expiration
            expiration_time = session.updated_at + timedelta(
                minutes=self.settings.session_timeout_minutes
            )

            if datetime.utcnow() > expiration_time:
                logger.warning(f"Session {session_id} has expired")
                self.delete_session(session_id)
                return None

            return session

        return None

    def get_form_schema(self, session_id: str) -> Optional[FormSchema]:
        """Get form schema for a session."""
        return self.form_schemas.get(session_id)

    def update_session(
        self, session_id: str, conversation_state: ConversationState
    ) -> bool:
        """Update session with new conversation state."""
        if session_id in self.sessions:
            conversation_state.updated_at = datetime.utcnow()
            self.sessions[session_id] = conversation_state
            return True
        return False

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            if session_id in self.form_schemas:
                del self.form_schemas[session_id]
            logger.info(f"Deleted session {session_id}")
            return True
        return False

    def list_sessions(self) -> list[str]:
        """List all active session IDs."""
        return list(self.sessions.keys())

    def cleanup_expired_sessions(self):
        """Remove expired sessions."""
        now = datetime.utcnow()
        expired = []

        for session_id, session in self.sessions.items():
            expiration_time = session.updated_at + timedelta(
                minutes=self.settings.session_timeout_minutes
            )
            if now > expiration_time:
                expired.append(session_id)

        for session_id in expired:
            self.delete_session(session_id)

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

    def _generate_welcome_message(self, form_schema: FormSchema) -> str:
        """Generate welcome message for new session."""
        message = f"Welcome! I'll help you fill out the {form_schema.form_name} form. "

        if form_schema.description:
            message += f"{form_schema.description} "

        message += (
            "You can speak naturally, and I'll extract the information and fill in the form fields. "
            "Just tell me the information you'd like to provide, and I'll ask clarifying questions if needed."
        )

        # Mention required fields
        required_fields = form_schema.get_required_fields()
        if required_fields:
            field_labels = [field.label for field in required_fields[:3]]
            message += f"\n\nRequired information includes: {', '.join(field_labels)}"
            if len(required_fields) > 3:
                message += f", and {len(required_fields) - 3} more fields."

        return message

    def get_session_summary(self, session_id: str) -> Optional[Dict]:
        """Get a summary of session state."""
        session = self.get_session(session_id)
        if not session:
            return None

        form_schema = self.get_form_schema(session_id)
        if not form_schema:
            return None

        return {
            "session_id": session_id,
            "form_id": session.form_state.form_id,
            "form_name": form_schema.form_name,
            "completion_percentage": session.form_state.get_completion_percentage(
                form_schema
            ),
            "completed_fields": len(session.form_state.completed_fields),
            "total_required_fields": len(form_schema.get_required_fields()),
            "missing_required": session.form_state.missing_required,
            "is_complete": session.form_state.is_complete(form_schema),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "message_count": len(session.messages),
        }


class RedisSessionManager(SessionManager):
    """
    Redis-based session manager for production use.
    Requires Redis connection.
    """

    def __init__(self, settings: Settings):
        super().__init__(settings)
        try:
            import redis
            self.redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=False,
            )
            self.redis_client.ping()
            logger.info("Connected to Redis for session management")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using in-memory storage.")
            self.redis_client = None

    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"session:{session_id}"

    def _schema_key(self, session_id: str) -> str:
        """Generate Redis key for form schema."""
        return f"schema:{session_id}"

    def create_session(
        self, form_schema: FormSchema, session_id: Optional[str] = None
    ) -> str:
        """Create session in Redis."""
        session_id = super().create_session(form_schema, session_id)

        if self.redis_client:
            try:
                # Store in Redis with expiration
                session = self.sessions[session_id]
                self.redis_client.setex(
                    self._session_key(session_id),
                    timedelta(minutes=self.settings.session_timeout_minutes),
                    session.model_dump_json(),
                )
                self.redis_client.setex(
                    self._schema_key(session_id),
                    timedelta(minutes=self.settings.session_timeout_minutes),
                    form_schema.model_dump_json(),
                )
            except Exception as e:
                logger.error(f"Failed to store session in Redis: {e}")

        return session_id

    def get_session(self, session_id: str) -> Optional[ConversationState]:
        """Get session from Redis."""
        if self.redis_client:
            try:
                data = self.redis_client.get(self._session_key(session_id))
                if data:
                    return ConversationState.model_validate_json(data)
            except Exception as e:
                logger.error(f"Failed to retrieve session from Redis: {e}")

        return super().get_session(session_id)

    def get_form_schema(self, session_id: str) -> Optional[FormSchema]:
        """Get form schema from Redis."""
        if self.redis_client:
            try:
                data = self.redis_client.get(self._schema_key(session_id))
                if data:
                    return FormSchema.model_validate_json(data)
            except Exception as e:
                logger.error(f"Failed to retrieve schema from Redis: {e}")

        return super().get_form_schema(session_id)

    def update_session(
        self, session_id: str, conversation_state: ConversationState
    ) -> bool:
        """Update session in Redis."""
        success = super().update_session(session_id, conversation_state)

        if success and self.redis_client:
            try:
                self.redis_client.setex(
                    self._session_key(session_id),
                    timedelta(minutes=self.settings.session_timeout_minutes),
                    conversation_state.model_dump_json(),
                )
            except Exception as e:
                logger.error(f"Failed to update session in Redis: {e}")

        return success

    def delete_session(self, session_id: str) -> bool:
        """Delete session from Redis."""
        success = super().delete_session(session_id)

        if self.redis_client:
            try:
                self.redis_client.delete(
                    self._session_key(session_id),
                    self._schema_key(session_id),
                )
            except Exception as e:
                logger.error(f"Failed to delete session from Redis: {e}")

        return success
