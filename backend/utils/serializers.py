"""
Serialization utilities for converting database objects to JSON-safe formats.

Handles:
- Converting bytes to strings
- Handling None values
- Ensuring all fields are JSON-serializable
"""

from typing import Any, Dict, List


def bytes_to_string(value: Any) -> Any:
    """
    Convert bytes to string, recurse through dicts and lists.
    
    Args:
        value: Any value (scalar, bytes, dict, list, etc.)
        
    Returns:
        The value with all bytes converted to strings
    """
    if isinstance(value, bytes):
        # Try to decode bytes as UTF-8
        try:
            return value.decode('utf-8')
        except (UnicodeDecodeError, AttributeError):
            # If it fails, convert to hex string for debugging
            return f"b'{value.hex()}'"
    elif isinstance(value, dict):
        # Recursively convert each value in the dict
        return {k: bytes_to_string(v) for k, v in value.items()}
    elif isinstance(value, list):
        # Recursively convert each item in the list
        return [bytes_to_string(item) for item in value]
    else:
        # Return as-is (int, float, str, None, bool, etc.)
        return value


def clean_for_json(obj: Any) -> Any:
    """
    Clean any Python object to be JSON-serializable.
    
    Converts:
    - bytes to strings
    - datetime to ISO format strings
    - decimal to float
    - None to None
    - Recursively handles dicts and lists
    
    Args:
        obj: Object to clean
        
    Returns:
        JSON-serializable object
    """
    from decimal import Decimal
    from datetime import datetime
    
    if isinstance(obj, bytes):
        return bytes_to_string(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(item) for item in obj]
    elif obj is None:
        return None
    else:
        # Assume it's a basic type (str, int, float, bool)
        return obj


def convert_model_to_dict(item: Any) -> Dict[str, Any]:
    """
    Convert a SQLAlchemy model to a dictionary with all bytes converted to strings.
    
    Args:
        item: SQLAlchemy model instance
        
    Returns:
        Dictionary with from_attributes, with bytes converted to strings
    """
    if hasattr(item, '__dict__'):
        # It's a SQLAlchemy model
        result = {}
        for key, value in item.__dict__.items():
            if not key.startswith('_'):
                result[key] = bytes_to_string(value)
        return result
    else:
        # It's already a dict or something else
        return bytes_to_string(item if isinstance(item, dict) else item.__dict__)
