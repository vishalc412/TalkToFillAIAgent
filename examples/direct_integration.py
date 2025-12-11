"""
Direct Integration Example - Using the agent as a library without API.

This example shows how to use the FormFillingAgent directly in your Python
application without starting an HTTP server.
"""

import asyncio
import json
from pathlib import Path
from src.agent import FormFillingAgent
from src.models import FormSchema, FormState, ConversationState
from src.speech_processor import SpeechProcessor
from src.config import get_settings


async def main():
    """Main function demonstrating direct agent integration."""

    # Load form schema
    form_path = Path(__file__).parent / "railway_booking_form.json"
    with open(form_path) as f:
        form_data = json.load(f)

    form_schema = FormSchema(**form_data)
    session_id = "direct-session-001"

    print("=" * 60)
    print("AI Voice Form Filling Agent - Direct Integration")
    print("=" * 60)
    print(f"\nForm: {form_schema.form_name}")
    print(f"Required fields: {len(form_schema.get_required_fields())}\n")

    # Initialize agent
    agent = FormFillingAgent(form_schema, session_id)

    # Initialize conversation state
    conversation = ConversationState(
        session_id=session_id,
        form_state=FormState(
            form_id=form_schema.form_id,
            session_id=session_id
        )
    )

    # Welcome message
    welcome_msg = f"Welcome! I'll help you fill the {form_schema.form_name}."
    conversation.add_message("assistant", welcome_msg)
    print(f"Agent: {welcome_msg}\n")

    # Simulate user conversation
    user_inputs = [
        "I want to travel from Delhi to Mumbai on January 20th",
        "2 passengers, AC 2-Tier class",
        "Window seats please",
        "My email is john.doe@example.com and phone is 9876543210"
    ]

    for user_input in user_inputs:
        print(f"User: {user_input}")

        # Process input directly (no HTTP API call)
        conversation = await agent.process_input(user_input, conversation)

        # Get agent's response
        agent_response = [msg for msg in conversation.messages if msg.role == "assistant"][-1]
        print(f"Agent: {agent_response.content}")

        # Show progress
        completion = conversation.form_state.get_completion_percentage(form_schema)
        filled = len(conversation.form_state.completed_fields)
        total = len(form_schema.get_required_fields())
        print(f"Progress: {filled}/{total} required fields ({completion:.0f}%)\n")

    # Show final form state
    print("=" * 60)
    print("Final Form State")
    print("=" * 60)

    for field_id, field_value in conversation.form_state.field_values.items():
        field = form_schema.get_field(field_id)
        status = "✓" if field_value.valid else "✗"
        print(f"{status} {field.label}: {field_value.value}")

    # Check completion
    if conversation.form_state.is_complete(form_schema):
        print("\n✓ Form is complete and ready to submit!")
    else:
        missing = conversation.form_state.missing_required
        print(f"\n✗ Missing required fields: {', '.join(missing)}")

    # Optional: Generate speech response
    settings = get_settings()
    if hasattr(settings, 'tts_provider') and settings.tts_provider:
        try:
            speech = SpeechProcessor(settings)
            final_message = "Thank you! Your form is now complete."
            audio_data = await speech.text_to_speech(final_message)

            # Save audio
            audio_path = Path("response.mp3")
            with open(audio_path, "wb") as f:
                f.write(audio_data)
            print(f"\n🔊 Audio response saved to: {audio_path}")
        except Exception as e:
            print(f"\nNote: Could not generate audio: {e}")


def example_with_custom_handler():
    """
    Example showing how to integrate with custom logic.
    Perfect for building desktop apps, CLI tools, or automation scripts.
    """

    async def process_with_validation(form_schema, user_inputs):
        """Process inputs with custom validation logic."""
        agent = FormFillingAgent(form_schema, "custom-session")
        conversation = ConversationState(
            session_id="custom-session",
            form_state=FormState(
                form_id=form_schema.form_id,
                session_id="custom-session"
            )
        )

        results = []
        for user_input in user_inputs:
            # Process
            conversation = await agent.process_input(user_input, conversation)

            # Custom validation or logging
            result = {
                "input": user_input,
                "completion": conversation.form_state.get_completion_percentage(form_schema),
                "fields_filled": len(conversation.form_state.completed_fields)
            }
            results.append(result)

            # Custom business logic
            if conversation.form_state.is_complete(form_schema):
                # Trigger your custom workflow
                print("✓ Form complete - triggering custom workflow")
                break

        return conversation, results

    # Example usage
    print("\n" + "=" * 60)
    print("Custom Integration Pattern")
    print("=" * 60)
    print("""
This pattern allows you to:
- Integrate with existing Python applications
- Add custom validation logic
- Trigger custom workflows
- Build desktop/CLI applications
- Use in Jupyter notebooks
- Batch process forms
    """)


if __name__ == "__main__":
    # Run direct integration
    asyncio.run(main())

    # Show custom integration pattern
    example_with_custom_handler()

    print("\n" + "=" * 60)
    print("Direct Integration Complete!")
    print("=" * 60)
    print("""
Key Benefits of Direct Integration:
✓ No HTTP server needed
✓ Lower latency (~10ms vs ~50-200ms)
✓ Simpler deployment
✓ Easy to customize
✓ Perfect for Python-only apps

Use Cases:
- Desktop applications (Tkinter, PyQt)
- CLI tools
- Jupyter notebooks
- Automation scripts
- Batch processing
- Internal tools
    """)
