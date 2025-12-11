"""
LangGraph-based agent for intelligent form filling.
"""

from typing import Dict, Any, TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import operator
import json
import logging

from src.models import (
    FormSchema,
    FormState,
    ConversationState,
    ExtractedData,
    FieldValue,
)
from src.form_validator import FormValidator
from src.llm_providers import get_llm_model

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State definition for the form-filling agent."""

    messages: Annotated[Sequence[BaseMessage], operator.add]
    form_schema: FormSchema
    form_state: FormState
    user_input: str
    extracted_data: Dict[str, Any]
    next_question: str
    needs_clarification: bool
    is_complete: bool


class FormFillingAgent:
    """LangGraph-based conversational form-filling agent."""

    def __init__(self, form_schema: FormSchema, session_id: str):
        """
        Initialize the form-filling agent.

        Args:
            form_schema: The form schema to fill
            session_id: Unique session identifier
        """
        self.form_schema = form_schema
        self.session_id = session_id
        self.llm = get_llm_model()
        self.validator = FormValidator()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("extract_data", self._extract_data_node)
        workflow.add_node("validate_data", self._validate_data_node)
        workflow.add_node("update_form", self._update_form_node)
        workflow.add_node("generate_response", self._generate_response_node)

        # Define edges
        workflow.set_entry_point("extract_data")
        workflow.add_edge("extract_data", "validate_data")
        workflow.add_edge("validate_data", "update_form")
        workflow.add_edge("update_form", "generate_response")
        workflow.add_edge("generate_response", END)

        return workflow.compile()

    def _create_extraction_prompt(self, state: AgentState) -> str:
        """Create the prompt for data extraction."""
        form_fields_description = self._format_form_fields()
        current_values = self._format_current_values(state["form_state"])

        prompt = f"""You are an intelligent form-filling assistant. Your task is to extract structured data from user's natural language input and map it to form fields.

FORM SCHEMA:
{form_fields_description}

CURRENT FORM STATE:
{current_values}

USER INPUT:
{state['user_input']}

CONVERSATION HISTORY:
{self._format_conversation_history(state['messages'][-5:])}

INSTRUCTIONS:
1. Carefully analyze the user's input
2. Extract values for form fields based on the user's speech
3. Validate extracted values against field constraints
4. Identify which required fields are still missing
5. If information is ambiguous or missing, note what clarification is needed

Return a JSON response with the following structure:
{{
    "extracted_fields": {{
        "field_id": "extracted_value",
        ...
    }},
    "confidence_scores": {{
        "field_id": 0.95,
        ...
    }},
    "validation_status": {{
        "field_id": "valid|invalid|unclear",
        ...
    }},
    "missing_mandatory": ["field_id1", "field_id2"],
    "clarification_needed": true|false,
    "clarification_question": "What specific clarification do you need?"
}}

IMPORTANT:
- Only extract fields mentioned or implied in the user's input
- Use field validation rules to check if values are appropriate
- For dates, convert natural language (e.g., "next Monday", "January 15th") to ISO format (YYYY-MM-DD)
- For select fields, match user input to available options (check voice_aliases)
- Assign confidence scores (0.0-1.0) based on clarity of input
- If user input is ambiguous, set clarification_needed to true
"""
        return prompt

    def _format_form_fields(self) -> str:
        """Format form fields for the prompt."""
        fields_desc = []
        for field in self.form_schema.fields:
            desc = f"""
Field: {field.id}
  Label: {field.label}
  Type: {field.type.value}
  Required: {field.required}
  Options: {field.options if field.options else 'N/A'}
  Voice Hints: {field.voice_hints or 'N/A'}
  Validation: {field.validation.model_dump() if field.validation else 'N/A'}
"""
            if field.voice_aliases:
                desc += f"  Voice Aliases: {json.dumps(field.voice_aliases)}\n"
            fields_desc.append(desc)

        return "\n".join(fields_desc)

    def _format_current_values(self, form_state: FormState) -> str:
        """Format current form values for the prompt."""
        if not form_state.field_values:
            return "No fields filled yet."

        values = []
        for field_id, field_value in form_state.field_values.items():
            field = self.form_schema.get_field(field_id)
            if field:
                values.append(
                    f"  {field.label} ({field_id}): {field_value.value} "
                    f"[{'Valid' if field_value.valid else 'Invalid'}]"
                )

        return "\n".join(values) if values else "No fields filled yet."

    def _format_conversation_history(self, messages: Sequence[BaseMessage]) -> str:
        """Format conversation history for the prompt."""
        if not messages:
            return "No previous conversation."

        history = []
        for msg in messages:
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            history.append(f"{role}: {msg.content}")

        return "\n".join(history)

    async def _extract_data_node(self, state: AgentState) -> Dict[str, Any]:
        """Extract structured data from user input."""
        logger.info(f"Extracting data from user input: {state['user_input']}")

        prompt = self._create_extraction_prompt(state)

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content="You are a precise data extraction assistant. Always respond with valid JSON."),
                HumanMessage(content=prompt)
            ])

            # Parse JSON response
            content = response.content
            # Try to extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            extracted = json.loads(content)

            logger.info(f"Extracted data: {extracted}")

            return {
                "extracted_data": extracted,
                "needs_clarification": extracted.get("clarification_needed", False),
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response content: {response.content}")
            return {
                "extracted_data": {},
                "needs_clarification": True,
                "next_question": "I'm sorry, I didn't quite understand that. Could you please rephrase?"
            }
        except Exception as e:
            logger.error(f"Error in data extraction: {e}")
            return {
                "extracted_data": {},
                "needs_clarification": True,
                "next_question": "I encountered an error. Could you please repeat that?"
            }

    async def _validate_data_node(self, state: AgentState) -> Dict[str, Any]:
        """Validate extracted data against form schema."""
        logger.info("Validating extracted data")

        extracted = state["extracted_data"]
        extracted_fields = extracted.get("extracted_fields", {})
        validation_results = {}

        for field_id, value in extracted_fields.items():
            field = self.form_schema.get_field(field_id)
            if field:
                is_valid, error_message = self.validator.validate_field(field, value)
                validation_results[field_id] = {
                    "valid": is_valid,
                    "error": error_message,
                }

        # Update extracted data with validation results
        extracted["validation_results"] = validation_results

        return {"extracted_data": extracted}

    async def _update_form_node(self, state: AgentState) -> Dict[str, Any]:
        """Update form state with validated data."""
        logger.info("Updating form state")

        form_state = state["form_state"]
        extracted = state["extracted_data"]
        extracted_fields = extracted.get("extracted_fields", {})
        validation_results = extracted.get("validation_results", {})

        # Update field values
        for field_id, value in extracted_fields.items():
            validation = validation_results.get(field_id, {})
            is_valid = validation.get("valid", True)
            error_message = validation.get("error")

            field_value = FieldValue(
                field_id=field_id,
                value=value,
                valid=is_valid,
                error_message=error_message,
                confidence=extracted.get("confidence_scores", {}).get(field_id, 1.0),
            )

            form_state.field_values[field_id] = field_value

            if is_valid and field_id not in form_state.completed_fields:
                form_state.completed_fields.append(field_id)

        # Update missing required fields
        required_fields = self.form_schema.get_required_fields()
        form_state.missing_required = [
            field.id
            for field in required_fields
            if field.id not in form_state.completed_fields
        ]

        # Check if form is complete
        is_complete = len(form_state.missing_required) == 0

        return {
            "form_state": form_state,
            "is_complete": is_complete,
        }

    async def _generate_response_node(self, state: AgentState) -> Dict[str, Any]:
        """Generate natural language response to user."""
        logger.info("Generating response")

        form_state = state["form_state"]
        extracted = state["extracted_data"]

        # If clarification is needed
        if state.get("needs_clarification") or extracted.get("clarification_needed"):
            clarification_question = extracted.get("clarification_question", "")
            if clarification_question:
                return {"next_question": clarification_question}

        # Build response based on what was filled
        response_parts = []

        # Confirm filled fields
        filled_fields = []
        for field_id, field_value in form_state.field_values.items():
            if field_value.valid:
                field = self.form_schema.get_field(field_id)
                if field:
                    filled_fields.append(f"{field.label}: {field_value.value}")

        if filled_fields:
            response_parts.append("I've filled in the following:")
            response_parts.extend([f"  • {field}" for field in filled_fields])

        # Report validation errors
        validation_results = extracted.get("validation_results", {})
        errors = [
            f"{self.form_schema.get_field(fid).label}: {result['error']}"
            for fid, result in validation_results.items()
            if not result.get("valid")
        ]

        if errors:
            response_parts.append("\nHowever, I found some issues:")
            response_parts.extend([f"  • {error}" for error in errors])

        # Ask about missing required fields
        if form_state.missing_required and not state.get("is_complete"):
            next_field = self.form_schema.get_field(form_state.missing_required[0])
            if next_field:
                response_parts.append(
                    f"\n{next_field.voice_hints or f'Please provide your {next_field.label}.'}"
                )

        # Form complete
        if state.get("is_complete"):
            response_parts.append(
                "\nGreat! All required fields are complete. "
                "Would you like to review the information before submitting?"
            )

        response = "\n".join(response_parts)

        return {"next_question": response}

    async def process_input(
        self, user_input: str, conversation_state: ConversationState
    ) -> ConversationState:
        """
        Process user input and update conversation state.

        Args:
            user_input: User's speech transcription
            conversation_state: Current conversation state

        Returns:
            Updated conversation state
        """
        # Add user message to history
        conversation_state.add_message("user", user_input)

        # Prepare initial state
        messages = [
            HumanMessage(content=msg.content) if msg.role == "user" else AIMessage(content=msg.content)
            for msg in conversation_state.messages[-10:]  # Last 10 messages for context
        ]

        initial_state: AgentState = {
            "messages": messages,
            "form_schema": self.form_schema,
            "form_state": conversation_state.form_state,
            "user_input": user_input,
            "extracted_data": {},
            "next_question": "",
            "needs_clarification": False,
            "is_complete": False,
        }

        # Run the graph
        try:
            final_state = await self.graph.ainvoke(initial_state)

            # Update conversation state
            conversation_state.form_state = final_state["form_state"]
            assistant_response = final_state.get("next_question", "")

            if assistant_response:
                conversation_state.add_message("assistant", assistant_response)

            return conversation_state

        except Exception as e:
            logger.error(f"Error processing input: {e}", exc_info=True)
            error_message = "I apologize, but I encountered an error. Could you please try again?"
            conversation_state.add_message("assistant", error_message)
            return conversation_state
