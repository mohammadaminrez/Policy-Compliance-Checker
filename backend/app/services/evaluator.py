import re
from typing import Any, Dict, List, Tuple, Callable
from datetime import datetime


class DynamicRuleEvaluator:
    """
    Schema-agnostic policy evaluation engine.
    Works with ANY JSON structure - discovers patterns dynamically.
    No assumptions about field names or policy structure.
    """

    # Flexible key names for field identification
    FIELD_KEYS = ["field", "attribute", "key", "name", "property", "condition", "metric", "factor", "dimension"]

    # Flexible key names for operator identification
    OP_KEYS = ["op", "operator", "operation", "equals", "is", "comparison", "must_be", "check"]

    # Flexible key names for value identification
    VALUE_KEYS = ["value", "expected", "target", "compare_to", "threshold", "limit", "minimum", "maximum"]

    # Operator aliases mapping (natural language to symbols)
    OPERATOR_ALIASES: Dict[str, str] = {
        # Equality
        "equals": "==",
        "equal": "==",
        "is": "==",
        "is_equal_to": "==",
        "equal_to": "==",
        "eq": "==",
        # Inequality
        "not_equal": "!=",
        "not_equals": "!=",
        "is_not": "!=",
        "not_equal_to": "!=",
        "ne": "!=",
        "neq": "!=",
        # Greater than
        "greater_than": ">",
        "greater": ">",
        "gt": ">",
        "more_than": ">",
        "above": ">",
        # Less than
        "less_than": "<",
        "less": "<",
        "lt": "<",
        "below": "<",
        "under": "<",
        # Greater than or equal
        "greater_than_or_equal": ">=",
        "greater_than_or_equal_to": ">=",
        "gte": ">=",
        "ge": ">=",
        "at_least": ">=",
        "minimum": ">=",
        # Less than or equal
        "less_than_or_equal": "<=",
        "less_than_or_equal_to": "<=",
        "lte": "<=",
        "le": "<=",
        "at_most": "<=",
        "maximum": "<=",
        # Containment
        "in": "in",
        "within": "in",
        "one_of": "in",
        "any_of": "in",
        "not_in": "not_in",
        "not_within": "not_in",
        "none_of": "not_in",
        # String operations
        "contains": "contains",
        "includes": "contains",
        "has": "contains",
        "not_contains": "not_contains",
        "does_not_contain": "not_contains",
        "excludes": "not_contains",
        "contains_any": "contains_any",
        "starts_with": "starts_with",
        "begins_with": "starts_with",
        "startswith": "starts_with",
        "ends_with": "ends_with",
        "endswith": "ends_with",
        "matches": "regex",
        "regex": "regex",
        "pattern": "regex",
        # Existence
        "exists": "exists",
        "is_present": "exists",
        "has_value": "exists",
        "not_exists": "not_exists",
        "is_absent": "not_exists",
        "no_value": "not_exists",
        "is_empty": "is_empty",
        "empty": "is_empty",
        "is_not_empty": "is_not_empty",
        "not_empty": "is_not_empty",
        "has_content": "is_not_empty",
    }

    # Safe operator registry - NO eval() or code execution
    OPS: Dict[str, Callable] = {
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        ">": lambda a, b: DynamicRuleEvaluator._gt(a, b),
        "<": lambda a, b: DynamicRuleEvaluator._lt(a, b),
        ">=": lambda a, b: DynamicRuleEvaluator._ge(a, b),
        "<=": lambda a, b: DynamicRuleEvaluator._le(a, b),
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
        "contains_any": lambda a, b: (
            (lambda actual_list, expected_list: any(x in set(expected_list) for x in actual_list))(
                DynamicRuleEvaluator._coerce_to_list(a),
                DynamicRuleEvaluator._coerce_to_list(b)
            )
        ) if b is not None else False,
    }

    @staticmethod
    def _coerce_to_list(value: Any) -> List[Any]:
        """Coerce strings with '|' or ',' into list; pass through lists/sets/tuples; wrap scalars."""
        if value is None:
            return []
        if isinstance(value, (list, set, tuple)):
            return list(value)
        if isinstance(value, str):
            text = value.strip()
            sep = "|" if "|" in text else ("," if "," in text else None)
            if sep:
                return [part.strip() for part in text.split(sep) if part.strip() != ""]
            return [text]
        return [value]

    @staticmethod
    def _try_parse_datetime(value: Any) -> datetime | None:
        if isinstance(value, str):
            s = value.strip()
            # Handle trailing Z (UTC)
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            try:
                return datetime.fromisoformat(s)
            except ValueError:
                return None
        return None

    @classmethod
    def _compare_datetime_or_number(cls, a: Any, b: Any) -> Tuple[Any, Any, str]:
        """Return comparable values and the mode used: 'datetime' or 'number'.
        Raises ValueError if neither can be compared."""
        da = cls._try_parse_datetime(a)
        db = cls._try_parse_datetime(b)
        if da is not None and db is not None:
            return da, db, "datetime"
        # fallback to numeric
        fa = float(a)
        fb = float(b)
        return fa, fb, "number"

    @classmethod
    def _gt(cls, a: Any, b: Any) -> bool:
        if a is None or b is None:
            return False
        x, y, _ = cls._compare_datetime_or_number(a, b)
        return x > y

    @classmethod
    def _lt(cls, a: Any, b: Any) -> bool:
        if a is None or b is None:
            return False
        x, y, _ = cls._compare_datetime_or_number(a, b)
        return x < y

    @classmethod
    def _ge(cls, a: Any, b: Any) -> bool:
        if a is None or b is None:
            return False
        x, y, _ = cls._compare_datetime_or_number(a, b)
        return x >= y

    @classmethod
    def _le(cls, a: Any, b: Any) -> bool:
        if a is None or b is None:
            return False
        x, y, _ = cls._compare_datetime_or_number(a, b)
        return x <= y

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

        # Normalize common wrapper styles (e.g., { matchType: 'ALL'|'ANY', rules/conditions: [...] })
        if isinstance(node, dict) and "rules" in node and isinstance(node["rules"], list):
            match_type = str(node.get("matchType", node.get("match_type", "ALL"))).upper()
            if match_type == "ANY":
                # Treat as anyOf
                return cls._evaluate_any_of(user, node["rules"])
            else:
                # Default to ALL
                return cls._evaluate_all_of(user, node["rules"])

        # Support alternate tree { matchType: 'AND'|'OR', conditions: [...] }
        if isinstance(node, dict) and "conditions" in node and isinstance(node["conditions"], list):
            match_type = str(node.get("matchType", node.get("match_type", "AND"))).upper()
            if match_type in ("ANY", "OR"):
                return cls._evaluate_any_of(user, node["conditions"])
            else:
                return cls._evaluate_all_of(user, node["conditions"])

        # Some formats wrap logical tree under a "condition" key
        if isinstance(node, dict) and "condition" in node:
            return cls.evaluate(user, node["condition"])  # recurse into condition tree

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
        Supports implicit operators (defaults to equality if no operator found).
        """
        # Dynamically find field name
        field = cls._find_key_value(rule, cls.FIELD_KEYS)

        # Dynamically find operator
        operator = cls._find_key_value(rule, cls.OP_KEYS)

        # Dynamically find expected value
        expected = cls._find_key_value(rule, cls.VALUE_KEYS)

        # IMPLICIT OPERATOR SUPPORT:
        # If no explicit operator/value pair found, treat rule as key-value pairs
        # Example: {"age": 18, "status": "active"} -> age==18 AND status=="active"
        if field is None and operator is None and expected is None:
            # This is an implicit equality check for all key-value pairs
            return cls._evaluate_implicit_conditions(user, rule)

        # DEFAULT OPERATOR: If field and value found but no operator, assume equality
        if field and expected is not None and operator is None:
            operator = "=="

        # Normalize operator (handle natural language aliases)
        if operator:
            operator_normalized = cls._normalize_operator(operator)
        else:
            operator_normalized = None

        # Get actual value from user data (handle nested keys with dot notation)
        actual = cls._get_nested_value(user, field) if field else None

        # Apply operator
        op_func = cls.OPS.get(operator_normalized) if operator_normalized else None

        if not op_func:
            # Unknown operator - fail safe
            return False, {
                "type": "condition",
                "field": field,
                "operator": operator,
                "operator_normalized": operator_normalized,
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
                "operator": operator_normalized,
                "expected": expected,
                "actual": actual,
                "passed": False,
                "error": str(e)
            }

        return passed, {
            "type": "condition",
            "field": field,
            "operator": operator_normalized,
            "expected": expected,
            "actual": actual,
            "passed": passed
        }

    @classmethod
    def _normalize_operator(cls, operator: str) -> str:
        """
        Normalize operator to canonical form.
        Handles natural language operators like 'greater_than' -> '>'
        """
        if not operator:
            return "=="

        # Convert to lowercase and replace spaces with underscores
        normalized = str(operator).lower().strip().replace(" ", "_")

        # Check if it's an alias
        if normalized in cls.OPERATOR_ALIASES:
            return cls.OPERATOR_ALIASES[normalized]

        # Return as-is if already canonical
        return normalized

    @classmethod
    def _evaluate_implicit_conditions(cls, user: Dict[str, Any], rule: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Handle implicit operator format where the rule is just key-value pairs.
        Example: {"age": 18, "status": "active"} means age==18 AND status=="active"
        """
        # Filter out metadata keys (description, name, title, id, etc.)
        metadata_keys = {"description", "name", "title", "id", "policy_id", "rule_id", "validation_name"}

        conditions = []
        for key, value in rule.items():
            if key not in metadata_keys:
                # Each key-value pair is an equality check
                actual = cls._get_nested_value(user, key)
                passed = actual == value
                conditions.append({
                    "field": key,
                    "operator": "==",
                    "expected": value,
                    "actual": actual,
                    "passed": passed
                })

        if not conditions:
            # No valid conditions found
            return True, {"result": "no_implicit_conditions"}

        # All conditions must pass (implicit AND)
        all_passed = all(c["passed"] for c in conditions)

        return all_passed, {
            "type": "implicit_conditions",
            "passed": all_passed,
            "conditions": conditions
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

        # First, try literal key (supports flat structures with dots in keys)
        if isinstance(data, dict) and key in data:
            return data[key]

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

        failed_conditions = cls._collect_failed_conditions(details) if not passed else []

        return {
            "user_data": user_data,
            "policy": policy,
            "passed": passed,
            "details": details,
            "failed_conditions": failed_conditions,
        }

    @classmethod
    def evaluate_users_against_policies(
        cls,
        users: List[Dict[str, Any]],
        policies: List[Dict[str, Any]],
        user_contexts: List[Dict[str, Any]] | None = None,
        policy_contexts: List[Dict[str, Any]] | None = None,
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
                if user_contexts and user_index < len(user_contexts):
                    result["user_context"] = user_contexts[user_index]
                if policy_contexts and policy_index < len(policy_contexts):
                    result["policy_context"] = policy_contexts[policy_index]
                results.append(result)

        return results

    @classmethod
    def _collect_failed_conditions(cls, details: Any) -> List[Dict[str, Any]]:
        """
        Walk evaluation details recursively and collect failing leaf conditions.
        """
        failures: List[Dict[str, Any]] = []

        if isinstance(details, dict):
            detail_type = details.get("type")
            if detail_type == "condition":
                if not details.get("passed", False):
                    failures.append(
                        {
                            "field": details.get("field"),
                            "operator": details.get("operator"),
                            "expected": details.get("expected"),
                            "actual": details.get("actual"),
                            "error": details.get("error"),
                        }
                    )
            else:
                if "conditions" in details:
                    failures.extend(cls._collect_failed_conditions(details["conditions"]))
                if "condition" in details:
                    failures.extend(cls._collect_failed_conditions(details["condition"]))
        elif isinstance(details, list):
            for item in details:
                failures.extend(cls._collect_failed_conditions(item))

        return failures
