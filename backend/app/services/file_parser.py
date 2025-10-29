import csv
import json
from typing import List, Dict, Any, Union
from io import StringIO
from app.core.config import settings


class FileParser:
    """
    Schema-agnostic file parser.
    Accepts any CSV/JSON structure - no assumptions about fields or format.
    """

    @staticmethod
    def parse_csv(content: str) -> List[Dict[str, Any]]:
        """
        Parse CSV content into list of raw dictionaries.
        Converts values to appropriate types automatically.

        Args:
            content: CSV file content as string

        Returns:
            List of user data dictionaries (any structure)
        """
        try:
            csv_file = StringIO(content)
            reader = csv.DictReader(csv_file)
            users = []

            def _assign_nested(target: Dict[str, Any], dotted_key: str, value: Any) -> None:
                # If the literal key exists or no dot, assign directly
                if "." not in dotted_key:
                    target[dotted_key] = value
                    return
                # Build nested dicts for dot notation
                parts = [p for p in dotted_key.split(".") if p]
                if not parts:
                    return
                curr = target
                for p in parts[:-1]:
                    if p not in curr or not isinstance(curr[p], dict):
                        curr[p] = {}
                    curr = curr[p]  # type: ignore[index]
                curr[parts[-1]] = value

            for row in reader:
                # Convert values to appropriate types dynamically and support dot-notated headers
                user_data: Dict[str, Any] = {}
                for key, value in row.items():
                    converted = FileParser._convert_value(value)
                    # Prefer nested assignment when header contains dot
                    if key and "." in key:
                        _assign_nested(user_data, key, converted)
                    else:
                        user_data[key] = converted
                users.append(user_data)

            return users
        except Exception as e:
            raise ValueError(f"Invalid CSV format: {str(e)}")

    @staticmethod
    def parse_json(content: str) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Parse JSON content - returns whatever structure is provided.
        No assumptions about format.

        Args:
            content: JSON file content as string

        Returns:
            Parsed JSON (any structure)
        """
        try:
            data = json.loads(content)
            return data
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")

    @staticmethod
    def normalize_to_list(data: Any) -> List[Dict[str, Any]]:
        """
        Normalize any data structure to a list of dictionaries.
        Handles: single object, array, or nested structures.
        Uses configurable wrapper keys and optional heuristic detection.

        Args:
            data: Any JSON-parsed data

        Returns:
            List of dictionaries
        """
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Check for configured wrapper keys
            for key in settings.USER_WRAPPER_KEYS:
                if key in data and isinstance(data[key], list):
                    return data[key]

            # Try heuristic detection if enabled
            if settings.ENABLE_HEURISTIC_DETECTION:
                from app.api.routes import _find_largest_array
                largest_key, largest_array = _find_largest_array(
                    data,
                    settings.MIN_HEURISTIC_ARRAY_SIZE
                )
                if largest_key and len(largest_array) > 0:
                    return largest_array

            # Otherwise, treat as single record
            return [data]
        else:
            # Primitive value - wrap in a dict
            return [{"value": data}]

    @staticmethod
    def _convert_value(value: str) -> Any:
        """
        Convert string value to appropriate type intelligently.
        Tries: bool -> int -> float -> string

        Args:
            value: String value to convert

        Returns:
            Converted value (any type)
        """
        if not value or value.strip() == "":
            return None

        value = value.strip()

        # Try boolean
        if value.lower() in ["true", "false"]:
            return value.lower() == "true"

        # Try integer
        try:
            if "." not in value and "e" not in value.lower():
                return int(value)
        except ValueError:
            pass

        # Try float
        try:
            return float(value)
        except ValueError:
            pass

        # Return as string
        return value
