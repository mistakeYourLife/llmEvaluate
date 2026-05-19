# llmEvaluate Runbook

## 1. Python Environment

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

If editable install is not desired, install core packages directly:

```bash
.venv/bin/pip install fastapi uvicorn sqlalchemy alembic httpx pytest
```

## 2. Database

Apply migrations:

```bash
.venv/bin/alembic upgrade head
```

The default local database path is:

```text
./llm_evaluate.db
```

Override with:

```bash
export DATABASE_URL="sqlite+pysqlite:///./custom.db"
```

## 3. Backend Services

API service:

```bash
.venv/bin/uvicorn api.app:app --reload --port 8000
```

Admin service:

```bash
.venv/bin/uvicorn admin.app:app --reload --port 8001
```

## 4. Frontend

Install dependencies:

```bash
cd admin/web
npm install
```

Run dev server:

```bash
npm run dev
```

Build production assets:

```bash
npm run build
```

## 5. Verification

Backend tests:

```bash
.venv/bin/pytest -q
```

Frontend build:

```bash
cd admin/web
npm run build
```

## 6. Current Limitations

- streaming proxying is not implemented yet.
- judge quality still depends on the configured provider returning JSON in the expected evaluator format.
- admin web is a functional scaffold, not a finished product UI.
