"""
Unit tests for FastAPI endpoints.
"""

import pytest
from fastapi.testclient import TestClient
import json
from src.api import app
from src.models import FormSchema, FormField, FieldType


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_form():
    """Sample form schema."""
    return {
        "form_id": "test_form",
        "form_name": "Test Form",
        "fields": [
            {
                "id": "name",
                "label": "Name",
                "type": "text",
                "required": True,
            },
            {
                "id": "email",
                "label": "Email",
                "type": "email",
                "required": True,
            },
        ],
    }


class TestAPIEndpoints:
    """Test API endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert data["status"] == "running"

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_create_session(self, client, sample_form):
        """Test session creation."""
        response = client.post(
            "/sessions",
            json={"form_schema": sample_form},
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "welcome_message" in data
        assert len(data["session_id"]) > 0

    def test_get_session_info(self, client, sample_form):
        """Test getting session info."""
        # Create session first
        create_response = client.post(
            "/sessions",
            json={"form_schema": sample_form},
        )
        session_id = create_response.json()["session_id"]

        # Get session info
        response = client.get(f"/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "completion_percentage" in data

    def test_get_nonexistent_session(self, client):
        """Test getting non-existent session."""
        response = client.get("/sessions/nonexistent")
        assert response.status_code == 404

    def test_process_text_input(self, client, sample_form):
        """Test processing text input."""
        # Create session
        create_response = client.post(
            "/sessions",
            json={"form_schema": sample_form},
        )
        session_id = create_response.json()["session_id"]

        # Send text input
        response = client.post(
            f"/sessions/{session_id}/text",
            json={
                "session_id": session_id,
                "text": "My name is John Doe and my email is john@example.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "completion_percentage" in data
        assert data["session_id"] == session_id

    def test_get_form_state(self, client, sample_form):
        """Test getting form state."""
        # Create session
        create_response = client.post(
            "/sessions",
            json={"form_schema": sample_form},
        )
        session_id = create_response.json()["session_id"]

        # Get form state
        response = client.get(f"/sessions/{session_id}/form-state")
        assert response.status_code == 200
        data = response.json()
        assert "form_state" in data
        assert "completion_percentage" in data

    def test_get_conversation_history(self, client, sample_form):
        """Test getting conversation history."""
        # Create session
        create_response = client.post(
            "/sessions",
            json={"form_schema": sample_form},
        )
        session_id = create_response.json()["session_id"]

        # Get conversation
        response = client.get(f"/sessions/{session_id}/conversation")
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert len(data["messages"]) > 0  # Should have welcome message

    def test_delete_session(self, client, sample_form):
        """Test deleting a session."""
        # Create session
        create_response = client.post(
            "/sessions",
            json={"form_schema": sample_form},
        )
        session_id = create_response.json()["session_id"]

        # Delete session
        response = client.delete(f"/sessions/{session_id}")
        assert response.status_code == 200

        # Verify deletion
        get_response = client.get(f"/sessions/{session_id}")
        assert get_response.status_code == 404

    def test_list_sessions(self, client, sample_form):
        """Test listing all sessions."""
        # Create a session
        client.post("/sessions", json={"form_schema": sample_form})

        # List sessions
        response = client.get("/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "count" in data
        assert data["count"] > 0

    def test_reset_session(self, client, sample_form):
        """Test resetting a session."""
        # Create session
        create_response = client.post(
            "/sessions",
            json={"form_schema": sample_form},
        )
        session_id = create_response.json()["session_id"]

        # Add some data
        client.post(
            f"/sessions/{session_id}/text",
            json={
                "session_id": session_id,
                "text": "My name is John",
            },
        )

        # Reset session
        response = client.post(f"/sessions/{session_id}/reset")
        assert response.status_code == 200

        # Verify reset
        state_response = client.get(f"/sessions/{session_id}/form-state")
        state_data = state_response.json()
        # Should be back to 0% completion
        assert state_data["completion_percentage"] == 0.0


class TestAPIValidation:
    """Test API input validation."""

    def test_create_session_invalid_schema(self, client):
        """Test creating session with invalid schema."""
        response = client.post(
            "/sessions",
            json={"form_schema": {"invalid": "schema"}},
        )
        # Should return 422 for validation error
        assert response.status_code == 422

    def test_text_input_missing_session_id(self, client):
        """Test text input without session_id."""
        response = client.post(
            "/sessions/nonexistent/text",
            json={"text": "test"},
        )
        # Should return 404 for nonexistent session
        assert response.status_code in [404, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
