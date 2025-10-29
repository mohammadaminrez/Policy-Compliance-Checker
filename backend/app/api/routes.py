from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
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


def _build_user_contexts_from_file(users: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
    contexts: List[Dict[str, Any]] = []
    for index, user in enumerate(users):
        label = _derive_label(user, ["user_id", "id", "email", "username", "name"])
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
    """
    policies: List[Dict[str, Any]] = []
    contexts: List[Dict[str, Any]] = []

    def _append_policy(entry: Dict[str, Any], extra: Dict[str, Any] | None = None):
        index = len(policies)
        label = _derive_label(entry, ["name", "title", "id", "policy"])
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
        for position, item in enumerate(payload):
            if isinstance(item, dict):
                _append_policy(item, {"position": position})
    elif isinstance(payload, dict):
        if "policies" in payload and isinstance(payload["policies"], list):
            for position, item in enumerate(payload["policies"]):
                if isinstance(item, dict):
                    _append_policy(item, {"section": "policies", "position": position})
        else:
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


@router.post("/evaluate")
async def evaluate(
    users_file: UploadFile = File(...),
    policies_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Evaluate users against policies.
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
                label = _derive_label(entry, ["user_id", "id", "email", "username", "name"])
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
                for key in ["users", "data", "records", "items"]:
                    if key in raw and isinstance(raw[key], list):
                        for position, entry in enumerate(raw[key]):
                            if isinstance(entry, dict):
                                _append_user(entry, position=position)
                        extracted = True
                        break
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
