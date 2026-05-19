# llmEvaluate

`llmEvaluate` is a Python-based LLM evaluation platform with four core modules:

- `api`: OpenAI-compatible ingress and side-channel recording
- `admin`: management APIs and admin web UI
- `data`: shared ORM, repositories, migrations, schemas
- `task`: replay and evaluation jobs

## Current Scope

The repository currently includes:

- OpenAI-compatible `POST /v1/chat/completions`
- request and response recording into `recorded_request` and `recorded_response`
- provider management APIs
- recorded data browsing APIs
- execution task APIs
- evaluation task APIs
- worker replay job skeleton
- worker evaluation job skeleton
- React admin UI scaffold under `admin/web`

## Backend Setup

Create a local virtual environment and install dependencies:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

Run database migrations:

```bash
.venv/bin/alembic upgrade head
```

Run tests:

```bash
.venv/bin/pytest -q
```

## Run Services

Run API service:

```bash
.venv/bin/uvicorn api.app:app --reload --port 8000
```

Run admin service:

```bash
.venv/bin/uvicorn admin.app:app --reload --port 8001
```

Replay and evaluation jobs now use provider records from the database. Streaming proxying is still pending, but non-stream requests are fully routed through configured providers.

## Admin Web

Install frontend dependencies:

```bash
cd admin/web
npm install
```

Run the frontend:

```bash
npm run dev
```

Build the frontend:

```bash
npm run build
```

## Key Paths

- `api/`
- `admin/`
- `admin/web/`
- `data/`
- `task/`
- `alembic/`
- `docs/plans/`
