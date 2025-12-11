"""
Test client for the AI Voice Form Filling Agent API.
Demonstrates how to interact with the API programmatically.
"""

import requests
import json
import time
from pathlib import Path


class FormFillingClient:
    """Client for interacting with the Form Filling Agent API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id = None

    def create_session(self, form_schema_path: str) -> dict:
        """Create a new session with a form schema."""
        # Load form schema
        with open(form_schema_path, "r") as f:
            form_schema = json.load(f)

        response = requests.post(
            f"{self.base_url}/sessions",
            json={"form_schema": form_schema},
        )
        response.raise_for_status()

        data = response.json()
        self.session_id = data["session_id"]

        print(f"✓ Session created: {self.session_id}")
        print(f"✓ Welcome message: {data['welcome_message']}\n")

        return data

    def send_text(self, text: str) -> dict:
        """Send text input to the agent."""
        if not self.session_id:
            raise ValueError("No active session. Create a session first.")

        response = requests.post(
            f"{self.base_url}/sessions/{self.session_id}/text",
            json={"session_id": self.session_id, "text": text},
        )
        response.raise_for_status()

        data = response.json()

        print(f"User: {text}")
        print(f"Agent: {data['message']}")
        print(f"Completion: {data['completion_percentage']:.1f}%")
        print(f"Updated fields: {', '.join(data['updated_fields']) or 'None'}")
        print()

        return data

    def send_voice(self, audio_path: str, language: str = "en-US") -> dict:
        """Send voice input to the agent."""
        if not self.session_id:
            raise ValueError("No active session. Create a session first.")

        with open(audio_path, "rb") as f:
            files = {"audio": f}
            data = {"language": language}

            response = requests.post(
                f"{self.base_url}/sessions/{self.session_id}/voice",
                files=files,
                data=data,
            )
            response.raise_for_status()

        return response.json()

    def get_session_info(self) -> dict:
        """Get session information."""
        if not self.session_id:
            raise ValueError("No active session. Create a session first.")

        response = requests.get(f"{self.base_url}/sessions/{self.session_id}")
        response.raise_for_status()

        return response.json()

    def get_form_state(self) -> dict:
        """Get current form state."""
        if not self.session_id:
            raise ValueError("No active session. Create a session first.")

        response = requests.get(
            f"{self.base_url}/sessions/{self.session_id}/form-state"
        )
        response.raise_for_status()

        return response.json()

    def get_conversation(self, limit: int = 20) -> dict:
        """Get conversation history."""
        if not self.session_id:
            raise ValueError("No active session. Create a session first.")

        response = requests.get(
            f"{self.base_url}/sessions/{self.session_id}/conversation",
            params={"limit": limit},
        )
        response.raise_for_status()

        return response.json()

    def delete_session(self):
        """Delete the current session."""
        if not self.session_id:
            return

        response = requests.delete(f"{self.base_url}/sessions/{self.session_id}")
        response.raise_for_status()

        print(f"✓ Session {self.session_id} deleted\n")
        self.session_id = None


def test_railway_booking():
    """Test railway booking form with conversational input."""
    print("=" * 60)
    print("Testing Railway Booking Form")
    print("=" * 60 + "\n")

    client = FormFillingClient()

    # Create session
    client.create_session("examples/railway_booking_form.json")

    # Simulate user conversation
    conversations = [
        "I want to book a ticket from Delhi to Mumbai",
        "I want to travel next Monday",
        "2 passengers please",
        "AC 2-Tier class",
        "Window seat would be great",
        "My email is john.doe@example.com",
        "Phone number is 9876543210",
    ]

    for text in conversations:
        client.send_text(text)
        time.sleep(1)  # Small delay for readability

    # Get final form state
    form_state = client.get_form_state()
    print("\n" + "=" * 60)
    print("Final Form State:")
    print("=" * 60)
    print(json.dumps(form_state, indent=2))

    # Cleanup
    client.delete_session()


def test_job_application():
    """Test job application form with conversational input."""
    print("=" * 60)
    print("Testing Job Application Form")
    print("=" * 60 + "\n")

    client = FormFillingClient()

    # Create session
    client.create_session("examples/job_application_form.json")

    # Simulate user conversation
    conversations = [
        "My name is Sarah Johnson and I'm applying for the Software Engineer position",
        "I have 5 years of experience and I'm currently in San Francisco",
        "My email is sarah.j@example.com and phone is 555-0123",
        "I have a Master's degree in Computer Science",
        "My notice period is 30 days",
        "I'm available for an interview starting next week",
    ]

    for text in conversations:
        client.send_text(text)
        time.sleep(1)

    # Get conversation history
    conversation = client.get_conversation()
    print("\n" + "=" * 60)
    print("Conversation History:")
    print("=" * 60)
    for msg in conversation["messages"]:
        role = msg["role"].upper()
        print(f"{role}: {msg['content']}\n")

    # Cleanup
    client.delete_session()


def test_multi_field_extraction():
    """Test extraction of multiple fields from a single utterance."""
    print("=" * 60)
    print("Testing Multi-Field Extraction")
    print("=" * 60 + "\n")

    client = FormFillingClient()

    # Create session
    client.create_session("examples/railway_booking_form.json")

    # Send comprehensive input with multiple fields
    client.send_text(
        "I want to book a ticket from Bangalore to Delhi on January 20th "
        "for 3 passengers in AC 1st Class with window seats. "
        "My email is travel@example.com and phone is 9123456789"
    )

    # Check what got filled
    form_state = client.get_form_state()
    filled_fields = form_state["form_state"]["field_values"]

    print("\n" + "=" * 60)
    print("Fields Extracted from Single Utterance:")
    print("=" * 60)
    for field_id, field_data in filled_fields.items():
        print(f"  {field_id}: {field_data['value']}")

    # Cleanup
    client.delete_session()


if __name__ == "__main__":
    try:
        # Wait for API to be ready
        print("Checking API availability...")
        response = requests.get("http://localhost:8000/health", timeout=5)
        response.raise_for_status()
        print("✓ API is ready\n")

        # Run tests
        test_railway_booking()
        print("\n" + "=" * 80 + "\n")

        test_job_application()
        print("\n" + "=" * 80 + "\n")

        test_multi_field_extraction()

        print("\n" + "=" * 80)
        print("All tests completed successfully!")
        print("=" * 80)

    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API. Make sure the server is running.")
        print("Start the server with: python -m src.api")
    except Exception as e:
        print(f"ERROR: {e}")
