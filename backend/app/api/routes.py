from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings
from app.models.policy import Policy, EvaluationResult
from app.services.file_parser import FileParser
from app.services.evaluator import DynamicRuleEvaluator

router = APIRouter()


def _derive_label(data: Dict[str, Any], preferred_keys: List[str]) -> str | None:
    """Best-effort human-readable label for arbitrary data."""
    for key in preferred_keys:
        value = data.get(key)
        if isinstance(value, (str, int, float)):
            return str(value)

    for key, value in data.items():
        if isinstance(value, (str, int, float)):
            return f"{key}: {value}"
    return None


def _find_largest_array(data: Dict[str, Any], min_size: int = 1, max_depth: int = 3) -> tuple[str | None, List[Any]]:
    """
    Heuristic: Find the largest array in a dictionary with support for deep nesting.
    Recursively searches nested objects up to max_depth levels.
    Returns (key_path, array) or (None, []) if none found.
    Key_path uses dot notation for nested keys: "parent.child.array"
    """
    def _search_recursive(obj: Any, depth: int = 0, path: str = "") -> List[tuple[str, List[Any]]]:
        """Recursively search for arrays in nested structures"""
        results = []

        if not isinstance(obj, dict) or depth > max_depth:
            return results

        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key

            if isinstance(value, list) and len(value) >= min_size:
                # Found an array
                results.append((current_path, value))
            elif isinstance(value, dict):
                # Recurse into nested object
                results.extend(_search_recursive(value, depth + 1, current_path))

        return results

    # Find all arrays
    all_arrays = _search_recursive(data, 0, "")

    if not all_arrays:
        return None, []

    # Return the largest one
    largest = max(all_arrays, key=lambda x: len(x[1]))
    return largest[0], largest[1]


def _build_user_contexts_from_file(users: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
    contexts: List[Dict[str, Any]] = []
    for index, user in enumerate(users):
        label = _derive_label(user, settings.USER_LABEL_KEYS)
        contexts.append(
            {
                "label": label or f"User #{index + 1}",
                "source": source,
                "index": index,
            }
        )
    return contexts


def _normalize_policies_from_payload(
    payload: Any,
    source: str,
    policy_id: int | None = None
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Normalize arbitrary policy payloads into a flat list of policy dictionaries
    while preserving human-readable context.

    Uses configurable wrapper keys and optional heuristic detection.
    """
    policies: List[Dict[str, Any]] = []
    contexts: List[Dict[str, Any]] = []

    def _append_policy(entry: Dict[str, Any], extra: Dict[str, Any] | None = None):
        index = len(policies)
        label = _derive_label(entry, settings.POLICY_LABEL_KEYS)
        context: Dict[str, Any] = {
            "label": label or f"Policy #{index + 1}",
            "source": source,
            "index": index,
        }
        if policy_id is not None:
            context["policy_id"] = policy_id
        if extra:
            context.update(extra)
        policies.append(entry)
        contexts.append(context)

    if isinstance(payload, list):
        # Payload is already an array
        for position, item in enumerate(payload):
            if isinstance(item, dict):
                _append_policy(item, {"position": position})
    elif isinstance(payload, dict):
        # Try configured wrapper keys first
        found_wrapper = False
        for key in settings.POLICY_WRAPPER_KEYS:
            if key in payload and isinstance(payload[key], list):
                for position, item in enumerate(payload[key]):
                    if isinstance(item, dict):
                        _append_policy(item, {"section": key, "position": position})
                found_wrapper = True
                break

        # If no wrapper key found and heuristic detection enabled
        if not found_wrapper and settings.ENABLE_HEURISTIC_DETECTION:
            largest_key, largest_array = _find_largest_array(
                payload,
                settings.MIN_HEURISTIC_ARRAY_SIZE
            )
            if largest_key and len(largest_array) > 0:
                for position, item in enumerate(largest_array):
                    if isinstance(item, dict):
                        _append_policy(item, {"section": largest_key, "position": position, "detected": "heuristic"})
                found_wrapper = True

        # Otherwise treat entire dict as single policy
        if not found_wrapper:
            _append_policy(payload, None)
    else:
        raise ValueError("Policy file must contain object or array")

    if len(policies) == 0:
        raise ValueError("No policy entries found in payload")

    return policies, contexts


@router.post("/policies/upload")
async def upload_policy(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a policy JSON file.
    Schema-agnostic - accepts any valid JSON structure.
    """
    try:
        # Read file content
        content = await file.read()
        content_str = content.decode("utf-8")

        # Parse JSON (any structure)
        policy_data = FileParser.parse_json(content_str)

        # Store in database as raw JSON
        policy = Policy(
            name=file.filename,
            raw=policy_data,
            version=1
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)

        return {
            "message": "Policy uploaded successfully",
            "policy_id": policy.id,
            "filename": file.filename
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload policy: {str(e)}")


@router.get("/policies")
async def get_policies(db: Session = Depends(get_db)):
    """Get all uploaded policies"""
    policies = db.query(Policy).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "version": p.version,
            "created_at": p.created_at.isoformat(),
            "raw": p.raw
        }
        for p in policies
    ]


@router.delete("/policies/{policy_id}")
async def delete_policy(policy_id: int, db: Session = Depends(get_db)):
    """Delete a policy by ID"""
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    db.delete(policy)
    db.commit()
    return {"message": "Policy deleted successfully"}


class UpdatePolicyRequest(BaseModel):
    name: str | None = None
    raw: Any | None = None


@router.put("/policies/{policy_id}")
async def update_policy(policy_id: int, payload: UpdatePolicyRequest, db: Session = Depends(get_db)):
    """Update a policy's name and/or raw JSON; bump version."""
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    try:
        if payload.name is not None:
            policy.name = payload.name

        if payload.raw is not None:
            # Accept any JSON structure (dict, list, primitives) as raw content
            policy.raw = payload.raw

        # Only bump version if anything changed
        if payload.name is not None or payload.raw is not None:
            current_version = policy.version or 0
            policy.version = current_version + 1

        db.add(policy)
        db.commit()
        db.refresh(policy)

        return {
            "id": policy.id,
            "name": policy.name,
            "version": policy.version,
            "created_at": policy.created_at.isoformat(),
            "raw": policy.raw,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update policy: {str(e)}")


@router.post("/users/upload")
async def upload_users(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload user data file (CSV or JSON).
    Schema-agnostic - accepts any structure.
    Stores metadata temporarily.
    """
    try:
        # Read file content
        content = await file.read()
        content_str = content.decode("utf-8")

        # Determine file type and parse
        if file.filename.endswith(".csv"):
            users = FileParser.parse_csv(content_str)
        elif file.filename.endswith(".json"):
            data = FileParser.parse_json(content_str)
            users = FileParser.normalize_to_list(data)
        else:
            raise ValueError("File must be .csv or .json")

        # Store user data
        from app.models.policy import UserData
        user_data = UserData(raw={"filename": file.filename, "users": users})
        db.add(user_data)
        db.commit()
        db.refresh(user_data)

        return {
            "message": "Users uploaded successfully",
            "count": len(users),
            "id": user_data.id,
            "filename": file.filename
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload users: {str(e)}")


@router.get("/users")
async def get_users(db: Session = Depends(get_db)):
    """Get all uploaded user data"""
    from app.models.policy import UserData
    users = db.query(UserData).all()
    return [
        {
            "id": u.id,
            "filename": u.raw.get("filename", "unknown"),
            "count": len(u.raw.get("users", [])),
            "uploaded_at": u.uploaded_at.isoformat()
        }
        for u in users
    ]


@router.delete("/users/{user_id}")
async def delete_users(user_id: int, db: Session = Depends(get_db)):
    """Delete uploaded user data by ID"""
    from app.models.policy import UserData
    user_data = db.query(UserData).filter(UserData.id == user_id).first()
    if not user_data:
        raise HTTPException(status_code=404, detail="User data not found")

    db.delete(user_data)
    db.commit()
    return {"message": "User data deleted successfully"}


@router.post("/evaluate/ids")
async def evaluate_by_ids(
    policy_ids: List[int],
    user_ids: List[int],
    db: Session = Depends(get_db)
):
    """
    Evaluate selected users against selected policies from database.
    """
    try:
        from app.models.policy import UserData
        from app.services.evaluator import DynamicRuleEvaluator

        # Fetch selected policies
        policies_data = db.query(Policy).filter(Policy.id.in_(policy_ids)).all()
        if not policies_data:
            raise ValueError("No policies found with given IDs")

        # Fetch selected user data
        users_data = db.query(UserData).filter(UserData.id.in_(user_ids)).all()
        if not users_data:
            raise ValueError("No user data found with given IDs")

        # Collect all users from all selected user files using dynamic extraction
        all_users = []
        for user_data in users_data:
            raw = user_data.raw
            if isinstance(raw, dict):
                found_wrapper = False
                # Try configured wrapper keys
                for key in settings.USER_WRAPPER_KEYS:
                    if key in raw and isinstance(raw[key], list):
                        all_users.extend(raw[key])
                        found_wrapper = True
                        break

                # Try heuristic detection if enabled
                if not found_wrapper and settings.ENABLE_HEURISTIC_DETECTION:
                    largest_key, largest_array = _find_largest_array(
                        raw,
                        settings.MIN_HEURISTIC_ARRAY_SIZE
                    )
                    if largest_key and len(largest_array) > 0:
                        all_users.extend(largest_array)
                        found_wrapper = True

                # Otherwise treat as single user
                if not found_wrapper:
                    all_users.append(raw)
            elif isinstance(raw, list):
                all_users.extend(raw)

        # Collect all policies with metadata (which file they came from)
        all_policies_with_meta = []
        for policy_db in policies_data:
            policy_raw = policy_db.raw
            policy_file_name = policy_db.name  # The uploaded filename

            # Normalize to list if needed
            extracted_rules = []
            if isinstance(policy_raw, dict):
                found_wrapper = False
                # Try configured wrapper keys
                for key in settings.POLICY_WRAPPER_KEYS:
                    if key in policy_raw and isinstance(policy_raw[key], list):
                        extracted_rules = policy_raw[key]
                        found_wrapper = True
                        break

                # Try heuristic detection if enabled
                if not found_wrapper and settings.ENABLE_HEURISTIC_DETECTION:
                    largest_key, largest_array = _find_largest_array(
                        policy_raw,
                        settings.MIN_HEURISTIC_ARRAY_SIZE
                    )
                    if largest_key and len(largest_array) > 0:
                        extracted_rules = largest_array
                        found_wrapper = True

                # Otherwise treat as single policy
                if not found_wrapper:
                    extracted_rules = [policy_raw]
            elif isinstance(policy_raw, list):
                extracted_rules = policy_raw

            # Add metadata to each rule
            for idx, rule in enumerate(extracted_rules):
                all_policies_with_meta.append({
                    "rule": rule,
                    "policy_file": policy_file_name,
                    "rule_index": idx,
                    "policy_id": policy_db.id
                })

        # Extract just the rules for evaluation
        all_policies = [p["rule"] for p in all_policies_with_meta]

        # Evaluate
        raw_results = DynamicRuleEvaluator.evaluate_users_against_policies(all_users, all_policies)

        # Aggregate results by user, grouped by policy file
        user_results = {}
        for idx, result in enumerate(raw_results):
            user_key = str(result["user_data"])  # Use user data as key
            # Map back to the correct policy metadata using policy_index
            policy_index = result.get("policy_index")
            if policy_index is None or policy_index < 0 or policy_index >= len(all_policies_with_meta):
                # Skip inconsistent result to avoid index errors
                continue
            policy_meta = all_policies_with_meta[policy_index]

            if user_key not in user_results:
                user_results[user_key] = {
                    "user_data": result["user_data"],
                    "policy_files": {},  # Group by policy file
                    "total_rules": 0,
                    "passed_rules": 0,
                    "failed_rules": 0,
                    "all_passed": True,
                    "failed_conditions": []
                }

            policy_file = policy_meta["policy_file"]

            # Initialize policy file group if not exists
            if policy_file not in user_results[user_key]["policy_files"]:
                user_results[user_key]["policy_files"][policy_file] = {
                    "policy_file": policy_file,
                    "policy_id": policy_meta["policy_id"],
                    "rules": [],
                    "total_rules": 0,
                    "passed_rules": 0,
                    "failed_rules": 0
                }

            # Add rule result to policy file group
            policy_file_group = user_results[user_key]["policy_files"][policy_file]
            policy_file_group["rules"].append({
                "rule": result["policy"],
                "rule_index": policy_meta["rule_index"],
                "passed": result["passed"],
                "details": result["details"]
            })
            policy_file_group["total_rules"] += 1
            user_results[user_key]["total_rules"] += 1

            if result["passed"]:
                policy_file_group["passed_rules"] += 1
                user_results[user_key]["passed_rules"] += 1
            else:
                policy_file_group["failed_rules"] += 1
                user_results[user_key]["failed_rules"] += 1
                user_results[user_key]["all_passed"] = False
                # Collect failed conditions
                if "failed_conditions" in result:
                    user_results[user_key]["failed_conditions"].extend(result["failed_conditions"])

        # Convert to list
        aggregated_results = []
        for user_data in user_results.values():
            # Convert policy_files dict to list
            user_data["policy_files"] = list(user_data["policy_files"].values())
            aggregated_results.append(user_data)

        # Store aggregated results
        for result in aggregated_results:
            eval_result = EvaluationResult(
                user_data=result["user_data"],
                policy_data={"policy_files": result["policy_files"]},
                passed=str(result["all_passed"]),
                details={
                    "total_rules": result["total_rules"],
                    "passed_rules": result["passed_rules"],
                    "failed_rules": result["failed_rules"],
                    "failed_conditions": result["failed_conditions"]
                }
            )
            db.add(eval_result)

        db.commit()

        return {
            "message": "Evaluation completed",
            "total_users": len(aggregated_results),
            "results": aggregated_results
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.post("/evaluate")
async def evaluate(
    users_file: UploadFile = File(...),
    policies_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Evaluate users against policies from file upload.
    Both files are schema-agnostic.

    Returns evaluation results with full transparency.
    """
    try:
        # Parse users file
        users_content = await users_file.read()
        users_content_str = users_content.decode("utf-8")

        if users_file.filename.endswith(".csv"):
            users = FileParser.parse_csv(users_content_str)
        elif users_file.filename.endswith(".json"):
            data = FileParser.parse_json(users_content_str)
            users = FileParser.normalize_to_list(data)
        else:
            raise ValueError("Users file must be .csv or .json")

        # Parse policies file
        policies_content = await policies_file.read()
        policies_content_str = policies_content.decode("utf-8")
        policy_data = FileParser.parse_json(policies_content_str)

        # Normalize policies into discrete entries while keeping metadata
        user_source = users_file.filename or "Uploaded Users"
        policy_source = policies_file.filename or "Uploaded Policies"
        user_contexts = _build_user_contexts_from_file(users, user_source)
        policies, policy_contexts = _normalize_policies_from_payload(policy_data, policy_source)

        # Evaluate dynamically
        results = DynamicRuleEvaluator.evaluate_users_against_policies(
            users,
            policies,
            user_contexts=user_contexts,
            policy_contexts=policy_contexts,
        )

        # Store results in database
        for result in results:
            details_payload = {
                "evaluation": result["details"],
                "failed_conditions": result.get("failed_conditions"),
                "user_context": result.get("user_context"),
                "policy_context": result.get("policy_context"),
            }
            eval_result = EvaluationResult(
                user_data=result["user_data"],
                policy_data=result["policy"],
                passed=str(result["passed"]),
                details=details_payload
            )
            db.add(eval_result)

        db.commit()

        return {
            "message": "Evaluation completed",
            "total_evaluations": len(results),
            "results": results
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.get("/results")
async def get_results(db: Session = Depends(get_db)):
    """Get all evaluation results"""
    results = db.query(EvaluationResult).order_by(EvaluationResult.evaluated_at.desc()).all()

    formatted_results = []
    for r in results:
        details_payload = r.details or {}
        if isinstance(details_payload, dict):
            evaluation_details = details_payload.get("evaluation", details_payload)
            user_context = details_payload.get("user_context")
            policy_context = details_payload.get("policy_context")
            failed_conditions = details_payload.get("failed_conditions")
        else:
            evaluation_details = details_payload
            user_context = None
            policy_context = None
            failed_conditions = None

        formatted_results.append(
            {
                "id": r.id,
                "user_data": r.user_data,
                "policy_data": r.policy_data,
                "passed": r.passed == "True",
                "details": evaluation_details,
                "user_context": user_context,
                "policy_context": policy_context,
                "failed_conditions": failed_conditions,
                "evaluated_at": r.evaluated_at.isoformat(),
            }
        )

    return formatted_results


@router.delete("/results")
async def clear_results(db: Session = Depends(get_db)):
    """Clear all evaluation results"""
    db.query(EvaluationResult).delete()
    db.commit()
    return {"message": "All results cleared"}


class EvaluationSelectionRequest(BaseModel):
    user_ids: List[int]
    policy_ids: List[int]


@router.post("/evaluate/selection")
async def evaluate_by_selection(
    selection: EvaluationSelectionRequest,
    db: Session = Depends(get_db)
):
    """
    Evaluate selected users and policies by database IDs.

    Body:
      { "user_ids": [int], "policy_ids": [int] }
    """
    try:
        from app.models.policy import UserData

        # Fetch user data records
        user_records = (
            db.query(UserData)
            .filter(UserData.id.in_(selection.user_ids))
            .all()
        )

        if len(user_records) == 0:
            raise HTTPException(status_code=404, detail="No user data found for given IDs")

        # Aggregate users list from stored raw payloads
        users: List[Dict[str, Any]] = []
        user_contexts: List[Dict[str, Any]] = []
        user_global_index = 0
        for record in user_records:
            raw = record.raw or {}
            filename = raw.get("filename") if isinstance(raw, dict) else None
            source_label = filename or f"UserData #{record.id}"

            def _append_user(entry: Dict[str, Any], position: int | None = None):
                nonlocal user_global_index
                label = _derive_label(entry, settings.USER_LABEL_KEYS)
                context: Dict[str, Any] = {
                    "label": label or f"User #{user_global_index + 1}",
                    "source": source_label,
                    "index": user_global_index,
                    "record_id": record.id,
                }
                if position is not None:
                    context["record_position"] = position
                if filename:
                    context["filename"] = filename
                users.append(entry)
                user_contexts.append(context)
                user_global_index += 1

            if isinstance(raw, dict):
                extracted = False
                # Try configured wrapper keys
                for key in settings.USER_WRAPPER_KEYS:
                    if key in raw and isinstance(raw[key], list):
                        for position, entry in enumerate(raw[key]):
                            if isinstance(entry, dict):
                                _append_user(entry, position=position)
                        extracted = True
                        break

                # Try heuristic detection if enabled
                if not extracted and settings.ENABLE_HEURISTIC_DETECTION:
                    largest_key, largest_array = _find_largest_array(
                        raw,
                        settings.MIN_HEURISTIC_ARRAY_SIZE
                    )
                    if largest_key and len(largest_array) > 0:
                        for position, entry in enumerate(largest_array):
                            if isinstance(entry, dict):
                                _append_user(entry, position=position)
                        extracted = True

                # Otherwise treat as single user
                if not extracted:
                    if isinstance(raw, dict):
                        _append_user(raw)
            elif isinstance(raw, list):
                for position, entry in enumerate(raw):
                    if isinstance(entry, dict):
                        _append_user(entry, position=position)

        # Fetch policy records
        policy_records = (
            db.query(Policy)
            .filter(Policy.id.in_(selection.policy_ids))
            .all()
        )

        if len(policy_records) == 0:
            raise HTTPException(status_code=404, detail="No policies found for given IDs")

        # Normalize policies to a flat list
        policies: List[Dict[str, Any]] = []
        policy_contexts: List[Dict[str, Any]] = []

        for p in policy_records:
            raw_policy = p.raw
            source_label = p.name or f"Policy #{p.id}"
            try:
                extracted_policies, extracted_contexts = _normalize_policies_from_payload(
                    raw_policy,
                    source_label,
                    policy_id=p.id
                )
            except ValueError:
                continue

            index_offset = len(policies)
            for context in extracted_contexts:
                context["index"] = context["index"] + index_offset
            policies.extend(extracted_policies)
            policy_contexts.extend(extracted_contexts)

        if not users:
            raise HTTPException(status_code=400, detail="Selected user data contains no users")
        if not policies:
            raise HTTPException(status_code=400, detail="Selected policies contain no rules")

        # Evaluate
        results = DynamicRuleEvaluator.evaluate_users_against_policies(
            users,
            policies,
            user_contexts=user_contexts,
            policy_contexts=policy_contexts,
        )

        # Store results
        for result in results:
            details_payload = {
                "evaluation": result["details"],
                "failed_conditions": result.get("failed_conditions"),
                "user_context": result.get("user_context"),
                "policy_context": result.get("policy_context"),
            }
            eval_result = EvaluationResult(
                user_data=result["user_data"],
                policy_data=result["policy"],
                passed=str(result["passed"]),
                details=details_payload
            )
            db.add(eval_result)
        db.commit()

        return {
            "message": "Evaluation completed",
            "selected_user_records": len(user_records),
            "selected_policy_records": len(policy_records),
            "total_users": len(users),
            "total_policies": len(policies),
            "total_evaluations": len(results),
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")
