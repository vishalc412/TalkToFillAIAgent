"""
FastAPI REST API for the AI Voice Form Filling Agent.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
import io

from src.config import get_settings
from src.models import FormSchema, AgentResponse
from src.agent import FormFillingAgent
from src.speech_processor import SpeechProcessor
from src.session_manager import SessionManager, RedisSessionManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Voice Form Filling Agent",
    description="Intelligent voice-driven form completion system",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
settings = get_settings()
session_manager = SessionManager(settings)
speech_processor = SpeechProcessor(settings)


# ==================== Request/Response Models ====================


class CreateSessionRequest(BaseModel):
    """Request to create a new session."""

    form_schema: FormSchema
    session_id: Optional[str] = None


class CreateSessionResponse(BaseModel):
    """Response with session details."""

    session_id: str
    welcome_message: str
    welcome_audio: Optional[str] = None  # Base64 encoded audio


class TextInputRequest(BaseModel):
    """Request with text input."""

    session_id: str
    text: str


class AgentResponseModel(BaseModel):
    """Agent response model."""

    session_id: str
    message: str
    audio: Optional[str] = None  # Base64 encoded audio
    form_state: Dict[str, Any]
    completion_percentage: float
    is_complete: bool
    updated_fields: List[str]
    validation_errors: List[Dict[str, str]]


class SessionInfoResponse(BaseModel):
    """Session information response."""

    session_id: str
    form_id: str
    form_name: str
    completion_percentage: float
    completed_fields: int
    total_required_fields: int
    missing_required: List[str]
    is_complete: bool
    created_at: str
    updated_at: str
    message_count: int


# ==================== API Endpoints ====================


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "AI Voice Form Filling Agent",
        "version": "1.0.0",
        "status": "running",
        "llm_provider": settings.llm_provider,
        "stt_provider": settings.stt_provider,
        "tts_provider": settings.tts_provider,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": "now"}


@app.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """
    Create a new form-filling session.

    Args:
        request: Form schema and optional session ID

    Returns:
        Session ID and welcome message
    """
    try:
        # Create session
        session_id = session_manager.create_session(
            request.form_schema, request.session_id
        )

        # Get welcome message
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=500, detail="Failed to create session")

        welcome_message = session.messages[0].content

        # Generate welcome audio
        welcome_audio = None
        try:
            audio_bytes = await speech_processor.text_to_speech(welcome_message)
            welcome_audio = speech_processor.audio_to_base64(audio_bytes)
        except Exception as e:
            logger.error(f"Failed to generate welcome audio: {e}")

        return CreateSessionResponse(
            session_id=session_id,
            welcome_message=welcome_message,
            welcome_audio=welcome_audio,
        )

    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}", response_model=SessionInfoResponse)
async def get_session_info(session_id: str):
    """
    Get information about a session.

    Args:
        session_id: Session identifier

    Returns:
        Session information
    """
    summary = session_manager.get_session_summary(session_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionInfoResponse(**summary)


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session.

    Args:
        session_id: Session identifier

    Returns:
        Success message
    """
    success = session_manager.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"message": "Session deleted successfully"}


@app.post("/sessions/{session_id}/text", response_model=AgentResponseModel)
async def process_text_input(session_id: str, request: TextInputRequest):
    """
    Process text input for a session.

    Args:
        session_id: Session identifier
        request: Text input

    Returns:
        Agent response with updated form state
    """
    try:
        # Get session
        conversation_state = session_manager.get_session(session_id)
        if not conversation_state:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get form schema
        form_schema = session_manager.get_form_schema(session_id)
        if not form_schema:
            raise HTTPException(status_code=404, detail="Form schema not found")

        # Create agent
        agent = FormFillingAgent(form_schema, session_id)

        # Process input
        updated_state = await agent.process_input(request.text, conversation_state)

        # Update session
        session_manager.update_session(session_id, updated_state)

        # Get latest assistant message
        assistant_messages = [
            msg for msg in updated_state.messages if msg.role == "assistant"
        ]
        latest_message = (
            assistant_messages[-1].content if assistant_messages else ""
        )

        # Generate audio response
        audio = None
        try:
            audio_bytes = await speech_processor.text_to_speech(latest_message)
            audio = speech_processor.audio_to_base64(audio_bytes)
        except Exception as e:
            logger.error(f"Failed to generate audio: {e}")

        # Build response
        return AgentResponseModel(
            session_id=session_id,
            message=latest_message,
            audio=audio,
            form_state=updated_state.form_state.model_dump(),
            completion_percentage=updated_state.form_state.get_completion_percentage(
                form_schema
            ),
            is_complete=updated_state.form_state.is_complete(form_schema),
            updated_fields=updated_state.form_state.completed_fields,
            validation_errors=[],  # TODO: Extract from form state
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing text input: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sessions/{session_id}/voice", response_model=AgentResponseModel)
async def process_voice_input(
    session_id: str,
    audio: UploadFile = File(...),
    language: str = Form("en-US"),
):
    """
    Process voice input for a session.

    Args:
        session_id: Session identifier
        audio: Audio file upload
        language: Language code

    Returns:
        Agent response with updated form state
    """
    try:
        # Get session
        conversation_state = session_manager.get_session(session_id)
        if not conversation_state:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get form schema
        form_schema = session_manager.get_form_schema(session_id)
        if not form_schema:
            raise HTTPException(status_code=404, detail="Form schema not found")

        # Read audio data
        audio_data = await audio.read()

        # Transcribe audio
        try:
            transcription = await speech_processor.speech_to_text(audio_data, language)
            logger.info(f"Transcribed: {transcription}")
        except Exception as e:
            logger.error(f"Failed to transcribe audio: {e}")
            raise HTTPException(status_code=400, detail="Failed to transcribe audio")

        # Create agent
        agent = FormFillingAgent(form_schema, session_id)

        # Process input
        updated_state = await agent.process_input(transcription, conversation_state)

        # Update session
        session_manager.update_session(session_id, updated_state)

        # Get latest assistant message
        assistant_messages = [
            msg for msg in updated_state.messages if msg.role == "assistant"
        ]
        latest_message = (
            assistant_messages[-1].content if assistant_messages else ""
        )

        # Generate audio response
        audio_response = None
        try:
            audio_bytes = await speech_processor.text_to_speech(latest_message)
            audio_response = speech_processor.audio_to_base64(audio_bytes)
        except Exception as e:
            logger.error(f"Failed to generate audio: {e}")

        # Build response
        return AgentResponseModel(
            session_id=session_id,
            message=latest_message,
            audio=audio_response,
            form_state=updated_state.form_state.model_dump(),
            completion_percentage=updated_state.form_state.get_completion_percentage(
                form_schema
            ),
            is_complete=updated_state.form_state.is_complete(form_schema),
            updated_fields=updated_state.form_state.completed_fields,
            validation_errors=[],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing voice input: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}/conversation")
async def get_conversation_history(session_id: str, limit: int = 20):
    """
    Get conversation history for a session.

    Args:
        session_id: Session identifier
        limit: Maximum number of messages to return

    Returns:
        Conversation messages
    """
    conversation_state = session_manager.get_session(session_id)
    if not conversation_state:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = conversation_state.get_recent_messages(limit)

    return {
        "session_id": session_id,
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
            }
            for msg in messages
        ],
    }


@app.get("/sessions/{session_id}/form-state")
async def get_form_state(session_id: str):
    """
    Get current form state for a session.

    Args:
        session_id: Session identifier

    Returns:
        Current form state
    """
    conversation_state = session_manager.get_session(session_id)
    if not conversation_state:
        raise HTTPException(status_code=404, detail="Session not found")

    form_schema = session_manager.get_form_schema(session_id)
    if not form_schema:
        raise HTTPException(status_code=404, detail="Form schema not found")

    return {
        "session_id": session_id,
        "form_state": conversation_state.form_state.model_dump(),
        "completion_percentage": conversation_state.form_state.get_completion_percentage(
            form_schema
        ),
        "is_complete": conversation_state.form_state.is_complete(form_schema),
    }


@app.get("/sessions")
async def list_sessions():
    """
    List all active sessions.

    Returns:
        List of session IDs
    """
    session_ids = session_manager.list_sessions()
    return {"sessions": session_ids, "count": len(session_ids)}


@app.post("/sessions/{session_id}/reset")
async def reset_session(session_id: str):
    """
    Reset a session (clear all field values but keep the form schema).

    Args:
        session_id: Session identifier

    Returns:
        Success message
    """
    conversation_state = session_manager.get_session(session_id)
    if not conversation_state:
        raise HTTPException(status_code=404, detail="Session not found")

    form_schema = session_manager.get_form_schema(session_id)
    if not form_schema:
        raise HTTPException(status_code=404, detail="Form schema not found")

    # Create new session with same ID and form schema
    session_manager.delete_session(session_id)
    session_manager.create_session(form_schema, session_id)

    return {"message": "Session reset successfully"}


# Background task for cleanup
@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("Starting AI Voice Form Filling Agent API")
    logger.info(f"LLM Provider: {settings.llm_provider}")
    logger.info(f"STT Provider: {settings.stt_provider}")
    logger.info(f"TTS Provider: {settings.tts_provider}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Shutting down AI Voice Form Filling Agent API")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
    )
