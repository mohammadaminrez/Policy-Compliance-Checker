# Policy Compliance Checker

> A schema-agnostic policy evaluation engine that evaluates user data against compliance rules without requiring predefined schemas.

## System Design

### Schema-Agnostic Architecture

Traditional policy engines require predefined schemas - any new data structure needs code changes. I designed this system to be **completely schema-agnostic** by discovering structure at runtime.

**Core Design Decisions:**

1. **No Hardcoded Schema**: All data stored as raw JSON. The system discovers field names, operators, and values dynamically at evaluation time.

2. **Three-Layer Pipeline**:
   - **FileParser Layer**: Handles CSV/JSON parsing with automatic type coercion (`"true"` → boolean, `"123"` → integer)
   - **Transform Layer** *(Planned)*: Will add data validation, enrichment, and pre-processing before evaluation
   - **Normalizer Layer**: Detects arrays using configurable wrapper keys (`policies`, `rules`, `users`, `data`) with fallback to heuristic detection
   - **Evaluator Layer**: Recursive tree-walker that handles nested policies with logical operators (`allOf`, `anyOf`, `not`)

3. **Dynamic Key Discovery**: Instead of expecting specific field names, the evaluator searches for common patterns:
   - Field keys: `field`, `attribute`, `property`, `key`
   - Operator keys: `op`, `operator`, `comparison`, `must_be`
   - Value keys: `value`, `expected`, `target`, `threshold`

4. **Operator Normalization**: Maps 100+ natural language operators to canonical forms (`greater_than` → `>`, `at_least` → `>=`)

5. **Fail-Safe Strategy**: Multiple fallback mechanisms ensure the system always produces a result:
   - Wrapper key detection → Heuristic array finding → Treat as single item

This design allows the same codebase to handle HR policies, financial rules, security checks, or any compliance scenario without modification.

## Tech Stack

- **Frontend**: React + TypeScript
- **Backend**: FastAPI (Python)
- **Database**: SQLite
- **Key Files**:
  - `backend/app/services/evaluator.py` - Core evaluation engine
  - `backend/app/services/file_parser.py` - CSV/JSON parser
  - `backend/app/api/routes.py` - API endpoints

---

## How to Run

### Option 1: Docker (Easiest)

```bash
docker-compose up
```

Then open:
- Frontend: http://localhost:80
- Backend API: http://localhost:8000/docs

### Option 2: Local Development

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm start
```
