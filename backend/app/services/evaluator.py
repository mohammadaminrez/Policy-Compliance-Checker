import re
from typing import Any, Dict, List, Tuple, Callable


class DynamicRuleEvaluator:
    """
    Schema-agnostic policy evaluation engine.
    Works with ANY JSON structure - discovers patterns dynamically.
    No assumptions about field names or policy structure.
    """

    # Flexible key names for field identification
    FIELD_KEYS = ["field", "attribute", "key", "name", "property"]

    # Flexible key names for operator identification
    OP_KEYS = ["op", "operator", "operation", "equals", "is", "comparison"]

    # Flexible key names for value identification
    VALUE_KEYS = ["value", "expected", "target", "compare_to"]

    # Safe operator registry - NO eval() or code execution
    OPS: Dict[str, Callable] = {
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        ">": lambda a, b: float(a) > float(b) if a is not None and b is not None else False,
        "<": lambda a, b: float(a) < float(b) if a is not None and b is not None else False,
        ">=": lambda a, b: float(a) >= float(b) if a is not None and b is not None else False,
        "<=": lambda a, b: float(a) <= float(b) if a is not None and b is not None else False,
        "in": lambda a, b: a in b if b is not None else False,
        "not_in": lambda a, b: a not in b if b is not None else True,
        "contains": lambda a, b: b in str(a) if a is not None else False,
        "not_contains": lambda a, b: b not in str(a) if a is not None else True,
        "regex": lambda a, b: bool(re.search(str(b), str(a))) if a is not None else False,
        "exists": lambda a, b: a is not None,
        "not_exists": lambda a, b: a is None,
        "starts_with": lambda a, b: str(a).startswith(str(b)) if a is not None else False,
        "ends_with": lambda a, b: str(a).endswith(str(b)) if a is not None else False,
        "is_empty": lambda a, b: not a if a is not None else True,
        "is_not_empty": lambda a, b: bool(a) if a is not None else False,
    }

    @classmethod
    def evaluate(cls, user: Dict[str, Any], node: Any) -> Tuple[bool, Dict[str, Any]]:
        """
        Recursively evaluate a policy node against user data.
        Discovers structure dynamically - no schema assumptions.

        Args:
            user: User data dictionary (any structure)
            node: Policy node (can be dict, list, or primitive)

        Returns:
            Tuple of (passed: bool, details: dict)
        """
        # Handle None or non-dict nodes
        if node is None:
            return True, {"result": "empty_node"}

        if not isinstance(node, dict):
            return True, {"result": "non_dict_node", "value": node}

        # Check for logical operators (allOf, anyOf, not)
        if "allOf" in node:
            return cls._evaluate_all_of(user, node["allOf"])

        if "anyOf" in node:
            return cls._evaluate_any_of(user, node["anyOf"])

        if "not" in node:
            return cls._evaluate_not(user, node["not"])

        # Check for alternative logical operator names
        if "and" in node:
            return cls._evaluate_all_of(user, node["and"])

        if "or" in node:
            return cls._evaluate_any_of(user, node["or"])

        # Otherwise, treat as a leaf rule (condition)
        return cls._evaluate_condition(user, node)

    @classmethod
    def _evaluate_all_of(cls, user: Dict[str, Any], conditions: List[Any]) -> Tuple[bool, Dict[str, Any]]:
        """Evaluate allOf (AND logic)"""
        results = []
        all_details = []

        for condition in conditions:
            passed, details = cls.evaluate(user, condition)
            results.append(passed)
            all_details.append(details)

        return all(results), {
            "type": "allOf",
            "passed": all(results),
            "conditions": all_details
        }

    @classmethod
    def _evaluate_any_of(cls, user: Dict[str, Any], conditions: List[Any]) -> Tuple[bool, Dict[str, Any]]:
        """Evaluate anyOf (OR logic)"""
        results = []
        all_details = []

        for condition in conditions:
            passed, details = cls.evaluate(user, condition)
            results.append(passed)
            all_details.append(details)

        return any(results), {
            "type": "anyOf",
            "passed": any(results),
            "conditions": all_details
        }

    @classmethod
    def _evaluate_not(cls, user: Dict[str, Any], condition: Any) -> Tuple[bool, Dict[str, Any]]:
        """Evaluate not (negation)"""
        passed, details = cls.evaluate(user, condition)

        return not passed, {
            "type": "not",
            "passed": not passed,
            "condition": details
        }

    @classmethod
    def _evaluate_condition(cls, user: Dict[str, Any], rule: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Evaluate a single condition (leaf rule).
        Dynamically discovers which keys represent field/operator/value.
        """
        # Dynamically find field name
        field = cls._find_key_value(rule, cls.FIELD_KEYS)

        # Dynamically find operator
        operator = cls._find_key_value(rule, cls.OP_KEYS)

        # Dynamically find expected value
        expected = cls._find_key_value(rule, cls.VALUE_KEYS)

        # Get actual value from user data (handle nested keys with dot notation)
        actual = cls._get_nested_value(user, field) if field else None

        # Apply operator
        op_func = cls.OPS.get(operator)

        if not op_func:
            # Unknown operator - fail safe
            return False, {
                "type": "condition",
                "field": field,
                "operator": operator,
                "expected": expected,
                "actual": actual,
                "passed": False,
                "error": "unknown_operator"
            }

        try:
            passed = op_func(actual, expected)
        except (TypeError, ValueError, AttributeError) as e:
            # Type mismatch or invalid comparison
            passed = False
            return passed, {
                "type": "condition",
                "field": field,
                "operator": operator,
                "expected": expected,
                "actual": actual,
                "passed": False,
                "error": str(e)
            }

        return passed, {
            "type": "condition",
            "field": field,
            "operator": operator,
            "expected": expected,
            "actual": actual,
            "passed": passed
        }

    @classmethod
    def _find_key_value(cls, node: Dict[str, Any], possible_keys: List[str]) -> Any:
        """
        Find the first matching key from a list of possible keys.
        Returns the value if found, None otherwise.
        """
        for key in possible_keys:
            if key in node:
                return node[key]
        return None

    @classmethod
    def _get_nested_value(cls, data: Dict[str, Any], key: str) -> Any:
        """
        Get value from nested dictionary using dot notation.
        Example: "address.city" -> data["address"]["city"]
        """
        if not key:
            return None

        keys = key.split(".")
        value = data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None

        return value

    @classmethod
    def evaluate_user_against_policy(
        cls,
        user_data: Dict[str, Any],
        policy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate a single user against a single policy.
        Completely schema-agnostic.

        Args:
            user_data: Raw user data (any structure)
            policy: Raw policy data (any structure)

        Returns:
            Evaluation result dictionary
        """
        # Evaluate the policy recursively
        passed, details = cls.evaluate(user_data, policy)

        return {
            "user_data": user_data,
            "policy": policy,
            "passed": passed,
            "details": details
        }

    @classmethod
    def evaluate_users_against_policies(
        cls,
        users: List[Dict[str, Any]],
        policies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Evaluate multiple users against multiple policies.

        Args:
            users: List of user data dictionaries
            policies: List of policy dictionaries

        Returns:
            List of evaluation results
        """
        results = []

        for user_index, user in enumerate(users):
            for policy_index, policy in enumerate(policies):
                result = cls.evaluate_user_against_policy(user, policy)
                result["user_index"] = user_index
                result["policy_index"] = policy_index
                results.append(result)

        return results
