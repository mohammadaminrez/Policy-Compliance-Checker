# Policy Compliance Checker

> A schema-agnostic policy evaluation engine that evaluates user data against compliance rules without requiring predefined schemas.

## What It Does

Upload a policy file (JSON) and user data (CSV/JSON), and the system checks which users pass or fail the compliance rules. Works with any data structure - no configuration needed.

## How It Works

1. **Upload Files**: User uploads policy rules (JSON) and user data (CSV/JSON)
2. **Parse**: System reads and converts files to structured data
3. **Normalize**: Finds arrays and labels automatically (no schema required)
4. **Evaluate**: Checks each user against each policy rule recursively
5. **Store**: Saves results to database
6. **Display**: Shows pass/fail results in a table

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
- Frontend: http://localhost:3000
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

---

## Example Usage

**1. Create policy.json:**
```json
{
  "policies": [
    {
      "name": "Age Check",
      "field": "age",
      "op": ">=",
      "value": 18
    }
  ]
}
```

**2. Create users.csv:**
```csv
user_id,age
john@email.com,25
jane@email.com,16
```

**3. Upload both files and click "Evaluate"**

**Result:**
- john@email.com: ✅ Pass
- jane@email.com: ❌ Fail

---

## Features

- Works with any JSON/CSV structure (no schema needed)
- Supports 100+ operators: `>`, `<`, `==`, `contains`, `starts_with`, etc.
- Handles nested data: `security.mfa_enabled`
- Logical operators: `allOf` (AND), `anyOf` (OR), `not`
- 17 test structures included in `test-data/`

---

## License

MIT
