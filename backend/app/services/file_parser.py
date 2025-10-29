import csv
import json
from typing import List, Dict, Any, Union
from io import StringIO


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

            for row in reader:
                # Convert values to appropriate types dynamically
                user_data = {}
                for key, value in row.items():
                    user_data[key] = FileParser._convert_value(value)
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

        Args:
            data: Any JSON-parsed data

        Returns:
            List of dictionaries
        """
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Check for common array wrapper keys
            for key in ["users", "data", "records", "items"]:
                if key in data and isinstance(data[key], list):
                    return data[key]
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
