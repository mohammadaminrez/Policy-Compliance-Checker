import os
from typing import List


class Settings:
    """
    Configuration for schema-agnostic behavior.
    All settings are customizable via environment variables.
    """

    # Policy wrapper keys - checked when normalizing policy files
    # Environment: POLICY_WRAPPER_KEYS (comma-separated)
    POLICY_WRAPPER_KEYS: List[str] = os.getenv(
        "POLICY_WRAPPER_KEYS",
        "policies,rules,checks,requirements,constraints,validations"
    ).split(",")

    # User data wrapper keys - checked when normalizing user files
    # Environment: USER_WRAPPER_KEYS (comma-separated)
    USER_WRAPPER_KEYS: List[str] = os.getenv(
        "USER_WRAPPER_KEYS",
        "users,data,records,items,entries,people"
    ).split(",")

    # Label key preferences for users - used for human-readable labels
    # Environment: USER_LABEL_KEYS (comma-separated)
    USER_LABEL_KEYS: List[str] = os.getenv(
        "USER_LABEL_KEYS",
        "user_id,id,email,username,name,first_name,last_name,display_name"
    ).split(",")

    # Label key preferences for policies - used for human-readable labels
    # Environment: POLICY_LABEL_KEYS (comma-separated)
    POLICY_LABEL_KEYS: List[str] = os.getenv(
        "POLICY_LABEL_KEYS",
        "name,title,id,policy,policy_id,policy_name,description"
    ).split(",")

    # Enable heuristic array detection (finds largest array automatically)
    # Environment: ENABLE_HEURISTIC_DETECTION (true/false)
    ENABLE_HEURISTIC_DETECTION: bool = os.getenv(
        "ENABLE_HEURISTIC_DETECTION",
        "true"
    ).lower() == "true"

    # Minimum array size to consider for heuristic detection
    # Environment: MIN_HEURISTIC_ARRAY_SIZE
    MIN_HEURISTIC_ARRAY_SIZE: int = int(os.getenv(
        "MIN_HEURISTIC_ARRAY_SIZE",
        "1"
    ))


settings = Settings()
