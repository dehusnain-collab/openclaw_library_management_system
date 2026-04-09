"""
Input validation utilities.
Covers: SCRUM-38, SCRUM-39
"""
import re
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, date
import html

from app.utils.logging import get_logger

logger = get_logger(__name__)


class InputValidator:
    """Class for input validation."""
    
    # Common validation patterns
    PATTERNS = {
        "email": r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        "phone": r'^\+?[1-9]\d{1,14}$',  # E.164 format
        "username": r'^[a-zA-Z0-9_]{3,30}$',
        "password": r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
        "isbn10": r'^\d{9}[\dX]$',
        "isbn13": r'^\d{13}$',
        "url": r'^https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/=]*)$',
        "ip_address": r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$',
        "date_iso": r'^\d{4}-\d{2}-\d{2}$',
        "datetime_iso": r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$',
    }
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """
        Sanitize a string input.
        
        Args:
            value: Input string
            max_length: Maximum length
            
        Returns:
            Sanitized string
        """
        if not value:
            return ""
        
        # Convert to string
        value = str(value)
        
        # Remove leading/trailing whitespace
        value = value.strip()
        
        # HTML escape
        value = html.escape(value)
        
        # Remove control characters
        value = re.sub(r'[\x00-\x1F\x7F]', '', value)
        
        # Limit length
        if len(value) > max_length:
            value = value[:max_length]
        
        return value
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """
        Validate email address.
        
        Args:
            email: Email address
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email:
            return False, "Email is required"
        
        email = email.strip()
        
        # Check length
        if len(email) > 254:
            return False, "Email is too long"
        
        # Check pattern
        if not re.match(InputValidator.PATTERNS["email"], email):
            return False, "Invalid email format"
        
        # Check for common disposable email domains
        disposable_domains = [
            "tempmail.com", "mailinator.com", "guerrillamail.com",
            "10minutemail.com", "throwawaymail.com", "yopmail.com"
        ]
        
        domain = email.split('@')[1].lower()
        if domain in disposable_domains:
            return False, "Disposable email addresses are not allowed"
        
        return True, "Email is valid"
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """
        Validate password strength.
        
        Args:
            password: Password
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not password:
            return False, "Password is required"
        
        # Check length
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if len(password) > 128:
            return False, "Password must be at most 128 characters long"
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        # Check for at least one digit
        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        
        # Check for at least one special character
        if not re.search(r'[@$!%*?&]', password):
            return False, "Password must contain at least one special character (@$!%*?&)"
        
        # Check for common passwords
        common_passwords = [
            "password", "123456", "qwerty", "admin", "letmein",
            "welcome", "monkey", "password1", "12345678", "abc123"
        ]
        
        if password.lower() in common_passwords:
            return False, "Password is too common"
        
        # Check for sequential characters
        if re.search(r'(.)\1{2,}', password):
            return False, "Password contains too many repeated characters"
        
        # Check for sequential numbers/letters
        sequences = [
            "0123456789", "9876543210",
            "abcdefghijklmnopqrstuvwxyz", "zyxwvutsrqponmlkjihgfedcba",
            "qwertyuiop", "asdfghjkl", "zxcvbnm"
        ]
        
        password_lower = password.lower()
        for seq in sequences:
            for i in range(len(seq) - 2):
                if seq[i:i+3] in password_lower:
                    return False, "Password contains sequential characters"
        
        return True, "Password is strong"
    
    @staticmethod
    def validate_username(username: str) -> Tuple[bool, str]:
        """
        Validate username.
        
        Args:
            username: Username
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not username:
            return False, "Username is required"
        
        username = username.strip()
        
        # Check length
        if len(username) < 3:
            return False, "Username must be at least 3 characters long"
        
        if len(username) > 30:
            return False, "Username must be at most 30 characters long"
        
        # Check pattern
        if not re.match(InputValidator.PATTERNS["username"], username):
            return False, "Username can only contain letters, numbers, and underscores"
        
        # Check for reserved usernames
        reserved_usernames = [
            "admin", "administrator", "root", "system", "support",
            "help", "info", "contact", "test", "demo"
        ]
        
        if username.lower() in reserved_usernames:
            return False, "This username is reserved"
        
        return True, "Username is valid"
    
    @staticmethod
    def validate_isbn(isbn: str) -> Tuple[bool, str, str]:
        """
        Validate ISBN (10 or 13).
        
        Args:
            isbn: ISBN number
            
        Returns:
            Tuple of (is_valid, error_message, isbn_type)
        """
        if not isbn:
            return False, "ISBN is required", ""
        
        isbn = isbn.strip().replace('-', '').replace(' ', '')
        
        # Check length
        if len(isbn) == 10:
            return InputValidator._validate_isbn10(isbn)
        elif len(isbn) == 13:
            return InputValidator._validate_isbn13(isbn)
        else:
            return False, "ISBN must be 10 or 13 digits", ""
    
    @staticmethod
    def _validate_isbn10(isbn: str) -> Tuple[bool, str, str]:
        """Validate ISBN-10."""
        # Check pattern
        if not re.match(InputValidator.PATTERNS["isbn10"], isbn):
            return False, "Invalid ISBN-10 format", "isbn10"
        
        # Calculate checksum
        total = 0
        for i in range(9):
            total += int(isbn[i]) * (10 - i)
        
        check_digit = isbn[9]
        if check_digit == 'X':
            total += 10
        else:
            total += int(check_digit)
        
        if total % 11 != 0:
            return False, "Invalid ISBN-10 checksum", "isbn10"
        
        return True, "ISBN-10 is valid", "isbn10"
    
    @staticmethod
    def _validate_isbn13(isbn: str) -> Tuple[bool, str, str]:
        """Validate ISBN-13."""
        # Check pattern
        if not re.match(InputValidator.PATTERNS["isbn13"], isbn):
            return False, "Invalid ISBN-13 format", "isbn13"
        
        # Calculate checksum
        total = 0
        for i in range(12):
            digit = int(isbn[i])
            if i % 2 == 0:
                total += digit
            else:
                total += digit * 3
        
        check_digit = (10 - (total % 10)) % 10
        
        if int(isbn[12]) != check_digit:
            return False, "Invalid ISBN-13 checksum", "isbn13"
        
        return True, "ISBN-13 is valid", "isbn13"
    
    @staticmethod
    def validate_date(date_str: str, date_format: str = "%Y-%m-%d") -> Tuple[bool, str, Optional[date]]:
        """
        Validate date string.
        
        Args:
            date_str: Date string
            date_format: Date format
            
        Returns:
            Tuple of (is_valid, error_message, date_object)
        """
        if not date_str:
            return False, "Date is required", None
        
        try:
            date_obj = datetime.strptime(date_str, date_format).date()
            
            # Check if date is in the future (for certain validations)
            if date_obj > datetime.now().date():
                return False, "Date cannot be in the future", date_obj
            
            return True, "Date is valid", date_obj
        except ValueError:
            return False, f"Invalid date format. Expected {date_format}", None
    
    @staticmethod
    def validate_number(
        value: Any,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        is_integer: bool = False
    ) -> Tuple[bool, str, Optional[Union[int, float]]]:
        """
        Validate number.
        
        Args:
            value: Number value
            min_value: Minimum value
            max_value: Maximum value
            is_integer: Whether value must be integer
            
        Returns:
            Tuple of (is_valid, error_message, number)
        """
        if value is None:
            return False, "Number is required", None
        
        try:
            if is_integer:
                num = int(value)
            else:
                num = float(value)
        except (ValueError, TypeError):
            return False, "Invalid number", None
        
        # Check min value
        if min_value is not None and num < min_value:
            return False, f"Number must be at least {min_value}", num
        
        # Check max value
        if max_value is not None and num > max_value:
            return False, f"Number must be at most {max_value}", num
        
        return True, "Number is valid", num
    
    @staticmethod
    def validate_string_length(
        value: str,
        min_length: int = 0,
        max_length: Optional[int] = None,
        required: bool = True
    ) -> Tuple[bool, str]:
        """
        Validate string length.
        
        Args:
            value: String value
            min_length: Minimum length
            max_length: Maximum length
            required: Whether value is required
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if required and not value:
            return False, "Value is required"
        
        if value is None:
            value = ""
        
        value = str(value)
        
        # Check min length
        if len(value) < min_length:
            return False, f"Value must be at least {min_length} characters long"
        
        # Check max length
        if max_length is not None and len(value) > max_length:
            return False, f"Value must be at most {max_length} characters long"
        
        return True, "Value is valid"
    
    @staticmethod
    def validate_choice(
        value: Any,
        choices: List[Any],
        required: bool = True
    ) -> Tuple[bool, str]:
        """
        Validate choice from list.
        
        Args:
            value: Value to check
            choices: List of valid choices
            required: Whether value is required
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if required and value is None:
            return False, "Value is required"
        
        if value is None:
            return True, "Value is valid (optional)"
        
        if value not in choices:
            return False, f"Value must be one of: {', '.join(str(c) for c in choices)}"
        
        return True, "Value is valid"
    
    @staticmethod
    def validate_json_schema(
        data: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> Tuple[bool, str, List[str]]:
        """
        Validate data against JSON schema.
        
        Args:
            data: Data to validate
            schema: JSON schema
            
        Returns:
            Tuple of (is_valid, error_message, errors)
        """
        errors = []
        
        for field, field_schema in schema.items():
            # Check if field is required
            is_required = field_schema.get("required", False)
            
            if is_required and field not in data:
                errors.append(f"Field '{field}' is required")
                continue
            
            if field not in data:
                continue
            
            value = data[field]
            
            # Validate type
            expected_type = field_schema.get("type")
            if expected_type:
                type_valid = InputValidator._validate_type(value, expected_type)
                if not type_valid:
                    errors.append(f"Field '{field}' must be of type {expected_type}")
                    continue
            
            # Validate min/max for numbers
            if expected_type in ["integer", "number"]:
                min_value = field_schema.get("min")
                max_value = field_schema.get("max")
                
                if min_value is not None and value < min_value:
                    errors.append(f"Field '{field}' must be at least {min_value}")
                
                if max_value is not None and value > max_value:
                    errors.append(f"Field '{field}' must be at most {max_value}")
            
            # Validate min/max length for strings
            if expected_type == "string":
                min_length = field_schema.get("minLength")
                max_length = field_schema.get("maxLength")
                
                if min_length is not None and len(str(value)) < min_length:
                    errors.append(f"Field '{field}' must be at least {min_length} characters long")
                
                if max_length is not None and len(str(value)) > max_length:
                    errors.append(f"Field '{field}' must be at most {max_length} characters long")
            
            # Validate pattern
            pattern = field_schema.get("pattern")
            if pattern and expected_type == "string":
                if not re.match(pattern, str(value)):
                    errors.append(f"Field '{field}' does not match required pattern")
            
            # Validate enum
            enum_values = field_schema.get("enum")
            if enum_values and value not in enum_values:
                errors.append(f"Field '{field}' must be one of: {', '.join(str(v) for v in enum_values)}")
        
        if errors:
            return False, "Validation failed", errors
        
        return True, "Validation passed", []
    
    @staticmethod
    def _validate_type(value: Any, expected_type: str) -> bool:
        """Validate value type."""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        
        if expected_type not in type_map:
            return True  # Unknown type, skip validation
        
        expected = type_map[expected_type]
        
        if isinstance(expected, tuple):
            return isinstance(value, expected)
        
        return isinstance(value, expected)
    
    @staticmethod
    def sanitize_and_validate_input(
        data: Dict[str, Any],
        validation_rules: Dict[str, Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Sanitize and validate input data.
        
        Args:
            data: Input data
            validation_rules: Validation rules
            
        Returns:
            Tuple of (sanitized_data, errors)
        """
        sanitized_data = {}
        errors = []
        
        for field, rules in validation_rules.items():
            value = data.get(field)
            
            # Check if field is required
            is_required = rules.get("required", False)
            
            if is_required and value is None:
                errors.append(f"Field '{field}' is required")
                continue
            
            if value is None:
                sanitized_data[field] = None
                continue
            
            # Sanitize based on type
            field_type = rules.get("type", "string")
            
            if field_type == "string":
                max_length = rules.get("max_length", 1000)
                sanitized_value = InputValidator.sanitize_string(str(value), max_length)
                
                # Validate length