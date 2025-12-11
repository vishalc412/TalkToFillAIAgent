"""
Form field validation engine.
"""

import re
from datetime import datetime
from typing import Tuple, Optional, Any
from dateutil import parser as date_parser
from src.models import FormField, FieldType, ValidationRule
import logging

logger = logging.getLogger(__name__)


class FormValidator:
    """Validates form field values against their validation rules."""

    @staticmethod
    def validate_field(
        field: FormField, value: Any
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a field value.

        Args:
            field: FormField definition
            value: Value to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if value is None or value == "":
            if field.required:
                return False, f"{field.label} is required"
            return True, None

        # Type-specific validation
        validator_map = {
            FieldType.EMAIL: FormValidator._validate_email,
            FieldType.PHONE: FormValidator._validate_phone,
            FieldType.URL: FormValidator._validate_url,
            FieldType.NUMBER: FormValidator._validate_number,
            FieldType.DATE: FormValidator._validate_date,
            FieldType.DATETIME: FormValidator._validate_datetime,
        }

        type_validator = validator_map.get(field.type)
        if type_validator:
            is_valid, error = type_validator(value, field)
            if not is_valid:
                return False, error

        # Validation rules
        if field.validation:
            is_valid, error = FormValidator._validate_rules(
                value, field.validation, field.label
            )
            if not is_valid:
                return False, error

        return True, None

    @staticmethod
    def _validate_email(value: Any, field: FormField) -> Tuple[bool, Optional[str]]:
        """Validate email format."""
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, str(value)):
            return False, f"{field.label} must be a valid email address"
        return True, None

    @staticmethod
    def _validate_phone(value: Any, field: FormField) -> Tuple[bool, Optional[str]]:
        """Validate phone number format."""
        # Remove common separators
        phone = re.sub(r"[\s\-\(\)\.]", "", str(value))
        # Check if it's a valid phone number (10-15 digits)
        if not re.match(r"^\+?\d{10,15}$", phone):
            return False, f"{field.label} must be a valid phone number"
        return True, None

    @staticmethod
    def _validate_url(value: Any, field: FormField) -> Tuple[bool, Optional[str]]:
        """Validate URL format."""
        url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        if not re.match(url_pattern, str(value), re.IGNORECASE):
            return False, f"{field.label} must be a valid URL"
        return True, None

    @staticmethod
    def _validate_number(value: Any, field: FormField) -> Tuple[bool, Optional[str]]:
        """Validate number."""
        try:
            num = float(value)
            if field.validation:
                if field.validation.min_value is not None and num < field.validation.min_value:
                    return False, f"{field.label} must be at least {field.validation.min_value}"
                if field.validation.max_value is not None and num > field.validation.max_value:
                    return False, f"{field.label} must be at most {field.validation.max_value}"
            return True, None
        except (ValueError, TypeError):
            return False, f"{field.label} must be a valid number"

    @staticmethod
    def _validate_date(value: Any, field: FormField) -> Tuple[bool, Optional[str]]:
        """Validate date."""
        try:
            if isinstance(value, str):
                date_value = date_parser.parse(value).date()
            elif isinstance(value, datetime):
                date_value = value.date()
            else:
                date_value = value

            if field.validation:
                today = datetime.now().date()

                if field.validation.future_only and date_value <= today:
                    return False, f"{field.label} must be a future date"

                if field.validation.past_only and date_value >= today:
                    return False, f"{field.label} must be a past date"

                if field.validation.min_date:
                    min_date = date_parser.parse(field.validation.min_date).date()
                    if date_value < min_date:
                        return False, f"{field.label} must be after {field.validation.min_date}"

                if field.validation.max_date:
                    max_date = date_parser.parse(field.validation.max_date).date()
                    if date_value > max_date:
                        return False, f"{field.label} must be before {field.validation.max_date}"

            return True, None
        except (ValueError, TypeError) as e:
            return False, f"{field.label} must be a valid date"

    @staticmethod
    def _validate_datetime(value: Any, field: FormField) -> Tuple[bool, Optional[str]]:
        """Validate datetime."""
        try:
            if isinstance(value, str):
                datetime_value = date_parser.parse(value)
            else:
                datetime_value = value

            if field.validation:
                now = datetime.now()

                if field.validation.future_only and datetime_value <= now:
                    return False, f"{field.label} must be a future date/time"

                if field.validation.past_only and datetime_value >= now:
                    return False, f"{field.label} must be a past date/time"

            return True, None
        except (ValueError, TypeError):
            return False, f"{field.label} must be a valid date/time"

    @staticmethod
    def _validate_rules(
        value: Any, rules: ValidationRule, field_label: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate against custom validation rules."""
        str_value = str(value)

        # Pattern validation
        if rules.pattern:
            if not re.match(rules.pattern, str_value):
                return False, f"{field_label} does not match required format"

        # Length validation
        if rules.min_length is not None and len(str_value) < rules.min_length:
            return False, f"{field_label} must be at least {rules.min_length} characters"

        if rules.max_length is not None and len(str_value) > rules.max_length:
            return False, f"{field_label} must be at most {rules.max_length} characters"

        return True, None

    @staticmethod
    def check_field_dependency(
        field: FormField, form_state: dict
    ) -> bool:
        """
        Check if field dependency is satisfied.

        Args:
            field: FormField to check
            form_state: Current form state with field values

        Returns:
            True if field should be shown/enabled
        """
        if not field.depends_on:
            return True

        dependent_field_value = form_state.get(field.depends_on.field)

        if field.depends_on.condition == "exists":
            return dependent_field_value is not None and dependent_field_value != ""

        if field.depends_on.condition == "equals":
            return dependent_field_value == field.depends_on.value

        if field.depends_on.condition == "not_equals":
            return dependent_field_value != field.depends_on.value

        if field.depends_on.condition == "contains":
            if isinstance(dependent_field_value, (list, tuple)):
                return field.depends_on.value in dependent_field_value
            return field.depends_on.value in str(dependent_field_value)

        if field.depends_on.condition == "greater_than":
            try:
                return float(dependent_field_value) > float(field.depends_on.value)
            except (ValueError, TypeError):
                return False

        if field.depends_on.condition == "less_than":
            try:
                return float(dependent_field_value) < float(field.depends_on.value)
            except (ValueError, TypeError):
                return False

        return True
