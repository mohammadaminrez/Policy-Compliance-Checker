from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime

from app.core.database import get_db
from app.models.policy import Policy, EvaluationResult
from app.services.file_parser import FileParser
from app.services.evaluator import DynamicRuleEvaluator

router = APIRouter()


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

        # Normalize policies to list
        if isinstance(policy_data, dict):
            # Check for common wrapper keys
            for key in ["policies", "rules", "checks"]:
                if key in policy_data and isinstance(policy_data[key], list):
                    policies = policy_data[key]
                    break
            else:
                # Treat whole object as single policy
                policies = [policy_data]
        elif isinstance(policy_data, list):
            policies = policy_data
        else:
            raise ValueError("Policy file must contain object or array")

        # Evaluate dynamically
        results = DynamicRuleEvaluator.evaluate_users_against_policies(users, policies)

        # Store results in database
        for result in results:
            eval_result = EvaluationResult(
                user_data=result["user_data"],
                policy_data=result["policy"],
                passed=str(result["passed"]),
                details=result["details"]
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

    return [
        {
            "id": r.id,
            "user_data": r.user_data,
            "policy_data": r.policy_data,
            "passed": r.passed == "True",
            "details": r.details,
            "evaluated_at": r.evaluated_at.isoformat()
        }
        for r in results
    ]


@router.delete("/results")
async def clear_results(db: Session = Depends(get_db)):
    """Clear all evaluation results"""
    db.query(EvaluationResult).delete()
    db.commit()
    return {"message": "All results cleared"}
