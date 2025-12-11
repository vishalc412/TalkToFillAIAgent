"""
Data models for form schemas, validation, and conversation state.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from enum import Enum


class FieldType(str, Enum):
    """Supported form field types."""

    TEXT = "text"
    EMAIL = "email"
    NUMBER = "number"
    DATE = "date"
    DATETIME = "datetime"
    SELECT = "select"
    MULTISELECT = "multiselect"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    TEXTAREA = "textarea"
    PHONE = "phone"
    URL = "url"


class ValidationRule(BaseModel):
    """Validation rules for form fields."""

    pattern: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_date: Optional[str] = None
    max_date: Optional[str] = None
    future_only: bool = False
    past_only: bool = False
    required_format: Optional[str] = None
    custom_validation: Optional[str] = None
    hints: List[str] = Field(default_factory=list)


class FieldDependency(BaseModel):
    """Field dependency configuration."""

    field: str
    condition: Literal["equals", "not_equals", "contains", "exists", "greater_than", "less_than"]
    value: Optional[Any] = None


class FormField(BaseModel):
    """Form field definition."""

    id: str
    label: str
    type: FieldType
    required: bool = False
    default_value: Optional[Any] = None
    placeholder: Optional[str] = None
    validation: Optional[ValidationRule] = None
    options: List[str] = Field(default_factory=list)
    voice_hints: Optional[str] = None
    voice_aliases: Dict[str, List[str]] = Field(default_factory=dict)
    depends_on: Optional[FieldDependency] = None
    help_text: Optional[str] = None
    group: Optional[str] = None


class FormSchema(BaseModel):
    """Complete form schema definition."""

    form_id: str
    form_name: str
    description: Optional[str] = None
    fields: List[FormField]
    multi_step: bool = False
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_field(self, field_id: str) -> Optional[FormField]:
        """Get a field by ID."""
        for field in self.fields:
            if field.id == field_id:
                return field
        return None

    def get_required_fields(self) -> List[FormField]:
        """Get all required fields."""
        return [field for field in self.fields if field.required]

    def get_fields_by_group(self, group: str) -> List[FormField]:
        """Get all fields in a specific group."""
        return [field for field in self.fields if field.group == group]


class FieldValue(BaseModel):
    """A field value with validation status."""

    field_id: str
    value: Any
    confidence: float = 1.0
    valid: bool = True
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class FormState(BaseModel):
    """Current state of form filling."""

    form_id: str
    session_id: str
    field_values: Dict[str, FieldValue] = Field(default_factory=dict)
    current_field: Optional[str] = None
    completed_fields: List[str] = Field(default_factory=list)
    missing_required: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    current_step: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_completion_percentage(self, form_schema: FormSchema) -> float:
        """Calculate form completion percentage."""
        required_fields = form_schema.get_required_fields()
        if not required_fields:
            return 100.0

        completed_required = sum(
            1 for field in required_fields if field.id in self.completed_fields
        )
        return (completed_required / len(required_fields)) * 100

    def is_complete(self, form_schema: FormSchema) -> bool:
        """Check if all required fields are completed."""
        required_field_ids = {field.id for field in form_schema.get_required_fields()}
        return required_field_ids.issubset(set(self.completed_fields))


class ConversationMessage(BaseModel):
    """A single message in the conversation."""

    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationState(BaseModel):
    """Complete conversation state."""

    session_id: str
    form_state: FormState
    messages: List[ConversationMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to conversation history."""
        message = ConversationMessage(
            role=role, content=content, metadata=metadata or {}
        )
        self.messages.append(message)
        self.updated_at = datetime.utcnow()

    def get_recent_messages(self, limit: int = 10) -> List[ConversationMessage]:
        """Get recent messages."""
        return self.messages[-limit:]


class ExtractedData(BaseModel):
    """Data extracted from user speech by LLM."""

    extracted_fields: Dict[str, Any] = Field(default_factory=dict)
    validation_status: Dict[str, str] = Field(default_factory=dict)
    missing_mandatory: List[str] = Field(default_factory=list)
    next_question: Optional[str] = None
    clarification_needed: bool = False
    clarification_question: Optional[str] = None
    confidence_scores: Dict[str, float] = Field(default_factory=dict)


class SpeechInput(BaseModel):
    """User speech input."""

    session_id: str
    audio_data: Optional[bytes] = None
    transcription: Optional[str] = None
    language: str = "en-US"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Response from the form-filling agent."""

    session_id: str
    form_state: FormState
    message: str
    tts_audio: Optional[bytes] = None
    next_action: Literal["continue", "clarify", "complete", "error"]
    updated_fields: List[str] = Field(default_factory=list)
    validation_errors: List[Dict[str, str]] = Field(default_factory=list)
    completion_percentage: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
