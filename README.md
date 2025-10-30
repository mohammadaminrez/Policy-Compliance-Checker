# Policy Compliance Checker

**Live Demo**: https://policy-compliance-checker.up.railway.app

---

## System Design

### Schema-Agnostic Architecture

My main goal was to build an engine that didn't require a predefined schema. I wanted to be able to feed it any user data and any policy and have it just work. This makes it flexible for any department, whether it's HR, security, or finance.

My design is built on a simple three-step data flow, with a "brain" (the evaluator) at the end.

**Mermaid Chart**: https://www.mermaidchart.com/d/e827e290-a91f-4a5c-bbc3-2322aa60f59f

---

### 1. The Data Flow

```
API → Parser → Normalizer → Evaluator
```

My FastAPI backend orchestrates this entire flow:

#### File Parsing (`file_parser.py`)

First, the raw files are sent to the FileParser service. Its only job is to turn files into Python objects. It's smart enough to convert CSVs into nested JSON (handling keys like `meta.profile.is_senior`) and automatically coerce types (like the string `"true"` to `True`, or `"123"` to the number `123`).

#### Normalization (`routes.py` helpers)

Just because we have objects doesn't mean we know where the data is. This step finds the actual lists. It looks for common wrapper keys (like `policies`, `users`, `data`, etc.) and has a fallback to just find the largest array in the file. This makes it schema-agnostic.

#### Evaluation (`evaluator.py`)

Once the API has a clean `List[users]` and `List[policies]`, it passes them to the DynamicRuleEvaluator. This is the "brain."

---

### 2. The "Brain": The DynamicRuleEvaluator Class

This is where the core logic lives. I designed it to be completely flexible:

#### Recursive & Secure
It's a recursive tree-walker that can handle any nested policy with operators like `allOf`, `anyOf`, and `not`. For security, it uses a safe dictionary of operators (no `eval()`).

#### Flexible Key Discovery
It doesn't look for a hardcoded `"field"` key. It searches for common names (`field`, `attribute`, `property`). It does the same for operators (`op`, `comparison`) and values (`value`, `expected`).

#### Natural Language Operators
It maps over 100 natural language aliases (`"at_least"`, `"greater_than"`) to their canonical symbols (`>=`, `>`), which makes writing policies easier.

#### Graceful Failure
As we proved in our tests, it handles data mismatches (like comparing `"Smith" > "M"`) by failing safely, not by crashing.

---

## Improvements Ideas

### Transform Layer

Add a dedicated Transform Layer between FileParser and Normalizer for:
- **Data Validation**: Validate input data before evaluation
- **Data Enrichment**: Add computed fields or external data
- **Pre-processing**: Clean and transform data before normalization
- **Schema Enforcement**: Optional schema validation for stricter use cases

This would make the pipeline: `API → FileParser → Transform → Normalizer → Evaluator`

---

## How to Run

### Option 1: Docker

```bash
docker-compose up
```

**Access:**
- Frontend: http://localhost
- Backend API: http://localhost:8000/docs

---

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
