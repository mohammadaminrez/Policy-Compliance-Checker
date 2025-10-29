#!/usr/bin/env python3
"""
Simple test script for the dynamic rule evaluator
"""
import sys
sys.path.insert(0, 'backend')

from app.services.evaluator import DynamicRuleEvaluator

# Test data
user = {
    "user_id": "test001",
    "password_length": 12,
    "mfa_enabled": True,
    "role": "admin",
    "account_age_days": 45
}

policy = {
    "allOf": [
        {
            "field": "password_length",
            "operator": ">=",
            "value": 8
        },
        {
            "field": "mfa_enabled",
            "operator": "==",
            "value": True
        }
    ]
}

# Run evaluation
print("Testing Dynamic Rule Evaluator")
print("=" * 50)
print(f"\nUser Data: {user}")
print(f"\nPolicy: {policy}")

passed, details = DynamicRuleEvaluator.evaluate(user, policy)

print(f"\nResult: {'PASSED' if passed else 'FAILED'}")
print(f"\nDetails: {details}")

# Test with failing user
failing_user = {
    "user_id": "test002",
    "password_length": 6,
    "mfa_enabled": False
}

print("\n" + "=" * 50)
print(f"\nFailing User: {failing_user}")

passed2, details2 = DynamicRuleEvaluator.evaluate(failing_user, policy)

print(f"\nResult: {'PASSED' if passed2 else 'FAILED'}")
print(f"\nDetails: {details2}")

print("\n" + "=" * 50)
print("Test completed successfully!")
