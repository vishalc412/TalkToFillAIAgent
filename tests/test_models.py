"""
Unit tests for the AI Voice Form Filling Agent.
"""

import pytest
from datetime import datetime, timedelta
from src.models import (
    FormSchema,
    FormField,
    FieldType,
    ValidationRule,
    FormState,
    ConversationState,
    FieldValue,
)
from src.form_validator import FormValidator


class TestFormValidator:
    """Test suite for FormValidator."""

    def test_validate_email_valid(self):
        """Test email validation with valid email."""
        field = FormField(
            id="email",
            label="Email",
            type=FieldType.EMAIL,
            required=True,
        )
        is_valid, error = FormValidator.validate_field(field, "test@example.com")
        assert is_valid
        assert error is None

    def test_validate_email_invalid(self):
        """Test email validation with invalid email."""
        field = FormField(
            id="email",
            label="Email",
            type=FieldType.EMAIL,
            required=True,
        )
        is_valid, error = FormValidator.validate_field(field, "invalid-email")
        assert not is_valid
        assert "valid email" in error.lower()

    def test_validate_required_field_empty(self):
        """Test required field validation when empty."""
        field = FormField(
            id="name",
            label="Name",
            type=FieldType.TEXT,
            required=True,
        )
        is_valid, error = FormValidator.validate_field(field, "")
        assert not is_valid
        assert "required" in error.lower()

    def test_validate_number_in_range(self):
        """Test number validation within valid range."""
        field = FormField(
            id="age",
            label="Age",
            type=FieldType.NUMBER,
            required=True,
            validation=ValidationRule(min_value=18, max_value=100),
        )
        is_valid, error = FormValidator.validate_field(field, 25)
        assert is_valid
        assert error is None

    def test_validate_number_out_of_range(self):
        """Test number validation outside valid range."""
        field = FormField(
            id="age",
            label="Age",
            type=FieldType.NUMBER,
            required=True,
            validation=ValidationRule(min_value=18, max_value=100),
        )
        is_valid, error = FormValidator.validate_field(field, 15)
        assert not is_valid
        assert "at least 18" in error.lower()

    def test_validate_phone_valid(self):
        """Test phone validation with valid number."""
        field = FormField(
            id="phone",
            label="Phone",
            type=FieldType.PHONE,
            required=True,
        )
        is_valid, error = FormValidator.validate_field(field, "9876543210")
        assert is_valid
        assert error is None

    def test_validate_phone_invalid(self):
        """Test phone validation with invalid number."""
        field = FormField(
            id="phone",
            label="Phone",
            type=FieldType.PHONE,
            required=True,
        )
        is_valid, error = FormValidator.validate_field(field, "123")
        assert not is_valid
        assert "valid phone" in error.lower()

    def test_validate_url_valid(self):
        """Test URL validation with valid URL."""
        field = FormField(
            id="website",
            label="Website",
            type=FieldType.URL,
            required=True,
        )
        is_valid, error = FormValidator.validate_field(field, "https://example.com")
        assert is_valid
        assert error is None

    def test_validate_date_future_only(self):
        """Test date validation with future_only constraint."""
        field = FormField(
            id="travel_date",
            label="Travel Date",
            type=FieldType.DATE,
            required=True,
            validation=ValidationRule(future_only=True),
        )

        # Future date should be valid
        future_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        is_valid, error = FormValidator.validate_field(field, future_date)
        assert is_valid

        # Past date should be invalid
        past_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        is_valid, error = FormValidator.validate_field(field, past_date)
        assert not is_valid

    def test_validate_string_length(self):
        """Test string length validation."""
        field = FormField(
            id="name",
            label="Name",
            type=FieldType.TEXT,
            required=True,
            validation=ValidationRule(min_length=2, max_length=50),
        )

        # Valid length
        is_valid, error = FormValidator.validate_field(field, "John Doe")
        assert is_valid

        # Too short
        is_valid, error = FormValidator.validate_field(field, "J")
        assert not is_valid

        # Too long
        is_valid, error = FormValidator.validate_field(field, "x" * 51)
        assert not is_valid


class TestFormSchema:
    """Test suite for FormSchema."""

    def test_get_field_existing(self):
        """Test getting an existing field."""
        schema = FormSchema(
            form_id="test_form",
            form_name="Test Form",
            fields=[
                FormField(id="name", label="Name", type=FieldType.TEXT, required=True),
                FormField(id="email", label="Email", type=FieldType.EMAIL, required=True),
            ],
        )
        field = schema.get_field("name")
        assert field is not None
        assert field.id == "name"

    def test_get_field_nonexistent(self):
        """Test getting a non-existent field."""
        schema = FormSchema(
            form_id="test_form",
            form_name="Test Form",
            fields=[
                FormField(id="name", label="Name", type=FieldType.TEXT, required=True),
            ],
        )
        field = schema.get_field("nonexistent")
        assert field is None

    def test_get_required_fields(self):
        """Test getting all required fields."""
        schema = FormSchema(
            form_id="test_form",
            form_name="Test Form",
            fields=[
                FormField(id="name", label="Name", type=FieldType.TEXT, required=True),
                FormField(id="email", label="Email", type=FieldType.EMAIL, required=True),
                FormField(id="notes", label="Notes", type=FieldType.TEXT, required=False),
            ],
        )
        required = schema.get_required_fields()
        assert len(required) == 2
        assert all(f.required for f in required)


class TestFormState:
    """Test suite for FormState."""

    def test_completion_percentage_empty(self):
        """Test completion percentage with no fields filled."""
        schema = FormSchema(
            form_id="test_form",
            form_name="Test Form",
            fields=[
                FormField(id="name", label="Name", type=FieldType.TEXT, required=True),
                FormField(id="email", label="Email", type=FieldType.EMAIL, required=True),
            ],
        )
        state = FormState(form_id="test_form", session_id="test_session")
        percentage = state.get_completion_percentage(schema)
        assert percentage == 0.0

    def test_completion_percentage_partial(self):
        """Test completion percentage with some fields filled."""
        schema = FormSchema(
            form_id="test_form",
            form_name="Test Form",
            fields=[
                FormField(id="name", label="Name", type=FieldType.TEXT, required=True),
                FormField(id="email", label="Email", type=FieldType.EMAIL, required=True),
            ],
        )
        state = FormState(
            form_id="test_form",
            session_id="test_session",
            completed_fields=["name"],
        )
        percentage = state.get_completion_percentage(schema)
        assert percentage == 50.0

    def test_completion_percentage_complete(self):
        """Test completion percentage with all fields filled."""
        schema = FormSchema(
            form_id="test_form",
            form_name="Test Form",
            fields=[
                FormField(id="name", label="Name", type=FieldType.TEXT, required=True),
                FormField(id="email", label="Email", type=FieldType.EMAIL, required=True),
            ],
        )
        state = FormState(
            form_id="test_form",
            session_id="test_session",
            completed_fields=["name", "email"],
        )
        percentage = state.get_completion_percentage(schema)
        assert percentage == 100.0

    def test_is_complete(self):
        """Test form completion check."""
        schema = FormSchema(
            form_id="test_form",
            form_name="Test Form",
            fields=[
                FormField(id="name", label="Name", type=FieldType.TEXT, required=True),
                FormField(id="email", label="Email", type=FieldType.EMAIL, required=True),
            ],
        )

        # Incomplete
        state = FormState(
            form_id="test_form",
            session_id="test_session",
            completed_fields=["name"],
        )
        assert not state.is_complete(schema)

        # Complete
        state.completed_fields = ["name", "email"]
        assert state.is_complete(schema)


class TestConversationState:
    """Test suite for ConversationState."""

    def test_add_message(self):
        """Test adding message to conversation."""
        state = ConversationState(
            session_id="test_session",
            form_state=FormState(form_id="test_form", session_id="test_session"),
        )

        initial_count = len(state.messages)
        state.add_message("user", "Hello")

        assert len(state.messages) == initial_count + 1
        assert state.messages[-1].role == "user"
        assert state.messages[-1].content == "Hello"

    def test_get_recent_messages(self):
        """Test getting recent messages."""
        state = ConversationState(
            session_id="test_session",
            form_state=FormState(form_id="test_form", session_id="test_session"),
        )

        # Add multiple messages
        for i in range(15):
            state.add_message("user", f"Message {i}")

        # Get last 10
        recent = state.get_recent_messages(10)
        assert len(recent) == 10
        assert recent[-1].content == "Message 14"


class TestFieldValue:
    """Test suite for FieldValue."""

    def test_field_value_creation(self):
        """Test creating a field value."""
        value = FieldValue(
            field_id="name",
            value="John Doe",
            confidence=0.95,
            valid=True,
        )

        assert value.field_id == "name"
        assert value.value == "John Doe"
        assert value.confidence == 0.95
        assert value.valid is True
        assert value.error_message is None
        assert isinstance(value.timestamp, datetime)


# Fixtures for integration tests
@pytest.fixture
def sample_form_schema():
    """Create a sample form schema for testing."""
    return FormSchema(
        form_id="railway_booking",
        form_name="Railway Booking",
        fields=[
            FormField(
                id="source",
                label="Source City",
                type=FieldType.TEXT,
                required=True,
            ),
            FormField(
                id="destination",
                label="Destination City",
                type=FieldType.TEXT,
                required=True,
            ),
            FormField(
                id="travel_date",
                label="Travel Date",
                type=FieldType.DATE,
                required=True,
                validation=ValidationRule(future_only=True),
            ),
            FormField(
                id="passengers",
                label="Passengers",
                type=FieldType.NUMBER,
                required=True,
                validation=ValidationRule(min_value=1, max_value=6),
            ),
            FormField(
                id="email",
                label="Email",
                type=FieldType.EMAIL,
                required=True,
            ),
        ],
    )


@pytest.fixture
def sample_conversation_state(sample_form_schema):
    """Create a sample conversation state."""
    return ConversationState(
        session_id="test_session",
        form_state=FormState(
            form_id=sample_form_schema.form_id,
            session_id="test_session",
        ),
    )


class TestIntegration:
    """Integration tests."""

    def test_full_form_validation_flow(self, sample_form_schema):
        """Test complete form validation workflow."""
        state = FormState(
            form_id=sample_form_schema.form_id,
            session_id="test_session",
        )

        # Fill fields with validation
        test_data = {
            "source": "Delhi",
            "destination": "Mumbai",
            "travel_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
            "passengers": 2,
            "email": "test@example.com",
        }

        for field_id, value in test_data.items():
            field = sample_form_schema.get_field(field_id)
            is_valid, error = FormValidator.validate_field(field, value)

            if is_valid:
                state.field_values[field_id] = FieldValue(
                    field_id=field_id,
                    value=value,
                    valid=True,
                )
                state.completed_fields.append(field_id)

        # Check completion
        assert state.is_complete(sample_form_schema)
        assert state.get_completion_percentage(sample_form_schema) == 100.0

    def test_conversation_flow(self, sample_conversation_state):
        """Test conversation flow."""
        conv = sample_conversation_state

        # Simulate conversation
        conv.add_message("assistant", "Welcome! How can I help?")
        conv.add_message("user", "I want to book a ticket")
        conv.add_message("assistant", "Sure! Where would you like to go?")
        conv.add_message("user", "From Delhi to Mumbai")

        # Check conversation
        assert len(conv.messages) >= 4

        # Check recent messages
        recent = conv.get_recent_messages(2)
        assert len(recent) == 2
        assert recent[-1].content == "From Delhi to Mumbai"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
