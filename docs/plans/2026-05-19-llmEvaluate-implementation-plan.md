# llmEvaluate Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first runnable version of llmEvaluate with four top-level modules: `api`, `admin`, `data`, and `task`, including OpenAI-compatible proxying, side-channel recording, replay execution tasks, independent evaluation tasks, and a minimal admin web UI.

**Architecture:** The project is a single repository with shared persistence in `data`, business entrypoints in `api` and `admin`, and offline execution in `task`. Replay execution and evaluation are modeled as separate task types so provider replay can be run independently from scoring. The implementation should start with a clean shared backend skeleton, then add persistence, then proxy and task flows, then the admin UI.

**Tech Stack:** Python, FastAPI, PostgreSQL, Redis, Celery or RQ, SQLAlchemy, Alembic, Pydantic, React, Vite.

---

### Task 1: Scaffold backend module layout

**Files:**
- Create: `api/__init__.py`
- Create: `api/app.py`
- Create: `admin/__init__.py`
- Create: `admin/app.py`
- Create: `task/__init__.py`
- Create: `task/worker.py`
- Create: `data/__init__.py`
- Create: `pyproject.toml`
- Create: `.gitignore`
- Test: `tests/test_imports.py`

**Step 1: Write the failing test**

```python
def test_backend_modules_import():
    import api.app
    import admin.app
    import task.worker
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_imports.py -v`
Expected: FAIL with import or module-not-found errors

**Step 3: Write minimal implementation**

- Add package directories and `__init__.py`.
- Add minimal FastAPI app objects in `api/app.py` and `admin/app.py`.
- Add a minimal worker entrypoint in `task/worker.py`.
- Add dependency declarations and Python version in `pyproject.toml`.
- Add Python and frontend ignores in `.gitignore`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_imports.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml .gitignore api admin task data tests/test_imports.py
git commit -m "chore: scaffold backend modules"
```

### Task 2: Create shared data layer and database bootstrap

**Files:**
- Create: `data/db.py`
- Create: `data/base.py`
- Create: `data/settings.py`
- Create: `data/models/__init__.py`
- Create: `tests/data/test_db_bootstrap.py`
- Modify: `pyproject.toml`

**Step 1: Write the failing test**

```python
def test_database_settings_and_base_import():
    from data.db import get_engine
    from data.base import Base
    assert get_engine is not None
    assert Base is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/data/test_db_bootstrap.py -v`
Expected: FAIL because data bootstrap files do not exist

**Step 3: Write minimal implementation**

- Add shared settings loader.
- Add SQLAlchemy base and engine/session factory bootstrap.
- Keep database URL configurable through environment variables.

**Step 4: Run test to verify it passes**

Run: `pytest tests/data/test_db_bootstrap.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add data pyproject.toml tests/data/test_db_bootstrap.py
git commit -m "feat: add shared database bootstrap"
```

### Task 3: Define core ORM models with audit fields

**Files:**
- Create: `data/models/provider.py`
- Create: `data/models/recording.py`
- Create: `data/models/dataset.py`
- Create: `data/models/execution.py`
- Create: `data/models/evaluation.py`
- Modify: `data/models/__init__.py`
- Test: `tests/data/test_models.py`

**Step 1: Write the failing test**

```python
def test_all_core_models_have_audit_fields():
    from data.models import Provider, RecordedRequest, ExecutionTask
    for model in [Provider, RecordedRequest, ExecutionTask]:
        assert hasattr(model, "created_at")
        assert hasattr(model, "updated_at")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/data/test_models.py -v`
Expected: FAIL because models are missing

**Step 3: Write minimal implementation**

- Add all approved ORM models.
- Share a timestamp mixin for `created_at` and `updated_at`.
- Keep JSON payload columns explicit.

**Step 4: Run test to verify it passes**

Run: `pytest tests/data/test_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add data/models tests/data/test_models.py
git commit -m "feat: add core ORM models"
```

### Task 4: Add Alembic migrations for the first schema

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/versions/<timestamp>_initial_schema.py`
- Test: `tests/data/test_migrations_smoke.py`

**Step 1: Write the failing test**

```python
def test_migration_files_exist():
    from pathlib import Path
    assert Path("alembic.ini").exists()
    assert Path("alembic/env.py").exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/data/test_migrations_smoke.py -v`
Expected: FAIL because migration files are missing

**Step 3: Write minimal implementation**

- Configure Alembic against the shared SQLAlchemy metadata.
- Create initial migration for all approved tables.

**Step 4: Run test to verify it passes**

Run: `pytest tests/data/test_migrations_smoke.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add alembic alembic.ini tests/data/test_migrations_smoke.py
git commit -m "feat: add initial database migration"
```

### Task 5: Implement provider repository and admin CRUD API

**Files:**
- Create: `data/repositories/provider_repository.py`
- Create: `admin/routes/providers.py`
- Modify: `admin/app.py`
- Create: `tests/admin/test_providers_api.py`

**Step 1: Write the failing test**

```python
def test_create_provider(client):
    response = client.post("/admin/providers", json={"name": "OpenAI", "code": "openai"})
    assert response.status_code == 201
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/admin/test_providers_api.py -v`
Expected: FAIL because the route does not exist

**Step 3: Write minimal implementation**

- Add provider repository methods.
- Add list, create, update, enable or disable endpoints.
- Keep API key handling isolated in the repository or service layer.

**Step 4: Run test to verify it passes**

Run: `pytest tests/admin/test_providers_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add admin data/repositories tests/admin/test_providers_api.py
git commit -m "feat: add provider management api"
```

### Task 6: Implement provider connectivity test endpoint

**Files:**
- Create: `api/providers/base.py`
- Create: `api/providers/openai_compatible.py`
- Modify: `admin/routes/providers.py`
- Create: `tests/admin/test_provider_test_endpoint.py`

**Step 1: Write the failing test**

```python
def test_provider_test_endpoint_returns_result(client):
    response = client.post("/admin/providers/1/test")
    assert response.status_code in (200, 400)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/admin/test_provider_test_endpoint.py -v`
Expected: FAIL because the endpoint does not exist

**Step 3: Write minimal implementation**

- Add provider adapter interface.
- Add one OpenAI-compatible adapter.
- Implement provider test endpoint with a lightweight health request.

**Step 4: Run test to verify it passes**

Run: `pytest tests/admin/test_provider_test_endpoint.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/providers admin/routes/providers.py tests/admin/test_provider_test_endpoint.py
git commit -m "feat: add provider connectivity test"
```

### Task 7: Implement recording repositories and schemas

**Files:**
- Create: `data/repositories/recording_repository.py`
- Create: `data/schemas/recording.py`
- Create: `tests/data/test_recording_repository.py`

**Step 1: Write the failing test**

```python
def test_recording_repository_can_store_request_and_response():
    from data.repositories.recording_repository import RecordingRepository
    assert RecordingRepository is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/data/test_recording_repository.py -v`
Expected: FAIL because the repository does not exist

**Step 3: Write minimal implementation**

- Add repository methods for request and response persistence.
- Add shared DTOs for request and response recording data.

**Step 4: Run test to verify it passes**

Run: `pytest tests/data/test_recording_repository.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add data/repositories data/schemas tests/data/test_recording_repository.py
git commit -m "feat: add recording persistence layer"
```

### Task 8: Implement OpenAI-compatible proxy endpoint in `api`

**Files:**
- Create: `api/routes/openai_proxy.py`
- Create: `api/services/proxy_service.py`
- Modify: `api/app.py`
- Create: `tests/api/test_chat_completions_proxy.py`

**Step 1: Write the failing test**

```python
def test_chat_completions_route_exists(client):
    response = client.post("/v1/chat/completions", json={"model": "test", "messages": []})
    assert response.status_code != 404
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_chat_completions_proxy.py -v`
Expected: FAIL because the route does not exist

**Step 3: Write minimal implementation**

- Add `/v1/chat/completions`.
- Accept OpenAI-compatible payloads.
- Resolve provider and forward the request.
- Return provider output transparently.

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_chat_completions_proxy.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api tests/api/test_chat_completions_proxy.py
git commit -m "feat: add chat completions proxy"
```

### Task 9: Add side-channel request and response recording to proxy flow

**Files:**
- Modify: `api/services/proxy_service.py`
- Modify: `data/repositories/recording_repository.py`
- Create: `tests/api/test_proxy_recording.py`

**Step 1: Write the failing test**

```python
def test_proxy_persists_recording_without_breaking_response(client):
    response = client.post("/v1/chat/completions", json={"model": "test", "messages": []})
    assert response.status_code in (200, 502)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_proxy_recording.py -v`
Expected: FAIL because recording is not integrated

**Step 3: Write minimal implementation**

- Save `recorded_request` before proxying.
- Save `recorded_response` after proxying.
- Do not fail the caller path if recording persistence fails.

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_proxy_recording.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/services/proxy_service.py data/repositories/recording_repository.py tests/api/test_proxy_recording.py
git commit -m "feat: record proxy requests and responses"
```

### Task 10: Add admin recording query APIs

**Files:**
- Create: `admin/routes/records.py`
- Modify: `admin/app.py`
- Create: `tests/admin/test_records_api.py`

**Step 1: Write the failing test**

```python
def test_records_list_route_exists(client):
    response = client.get("/admin/records")
    assert response.status_code != 404
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/admin/test_records_api.py -v`
Expected: FAIL because the route does not exist

**Step 3: Write minimal implementation**

- Add recorded data list endpoint.
- Add recorded data detail endpoint.
- Support time and provider filtering first.

**Step 4: Run test to verify it passes**

Run: `pytest tests/admin/test_records_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add admin/routes/records.py admin/app.py tests/admin/test_records_api.py
git commit -m "feat: add recorded data admin api"
```

### Task 11: Implement execution task models, repository, and service

**Files:**
- Create: `data/repositories/execution_repository.py`
- Create: `task/services/execution_service.py`
- Create: `tests/task/test_execution_service.py`

**Step 1: Write the failing test**

```python
def test_execution_service_exists():
    from task.services.execution_service import ExecutionService
    assert ExecutionService is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/task/test_execution_service.py -v`
Expected: FAIL because the service does not exist

**Step 3: Write minimal implementation**

- Add repository methods for execution tasks and execution results.
- Add service interface for creating and progressing replay tasks.

**Step 4: Run test to verify it passes**

Run: `pytest tests/task/test_execution_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add data/repositories/execution_repository.py task/services/execution_service.py tests/task/test_execution_service.py
git commit -m "feat: add execution task service"
```

### Task 12: Add admin APIs for execution task management

**Files:**
- Create: `admin/routes/execution_tasks.py`
- Modify: `admin/app.py`
- Create: `tests/admin/test_execution_tasks_api.py`

**Step 1: Write the failing test**

```python
def test_create_execution_task(client):
    response = client.post("/admin/execution-tasks", json={"name": "batch-1"})
    assert response.status_code != 404
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/admin/test_execution_tasks_api.py -v`
Expected: FAIL because the route does not exist

**Step 3: Write minimal implementation**

- Add create, list, detail, start, stop, retry endpoints for execution tasks.
- Add result listing endpoint for execution results.

**Step 4: Run test to verify it passes**

Run: `pytest tests/admin/test_execution_tasks_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add admin/routes/execution_tasks.py admin/app.py tests/admin/test_execution_tasks_api.py
git commit -m "feat: add execution task admin api"
```

### Task 13: Implement worker replay processing

**Files:**
- Modify: `task/worker.py`
- Create: `task/jobs/execution_job.py`
- Create: `tests/task/test_execution_job.py`

**Step 1: Write the failing test**

```python
def test_execution_job_entrypoint_exists():
    from task.jobs.execution_job import run_execution_task
    assert run_execution_task is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/task/test_execution_job.py -v`
Expected: FAIL because the job entrypoint does not exist

**Step 3: Write minimal implementation**

- Add worker-side execution job.
- Load source recordings.
- Call multiple providers.
- Persist `execution_result`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/task/test_execution_job.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add task/worker.py task/jobs/execution_job.py tests/task/test_execution_job.py
git commit -m "feat: add replay execution worker job"
```

### Task 14: Implement evaluation repository and evaluator interface

**Files:**
- Create: `data/repositories/evaluation_repository.py`
- Create: `task/evaluators/base.py`
- Create: `task/evaluators/llm_judge.py`
- Create: `tests/task/test_llm_judge_interface.py`

**Step 1: Write the failing test**

```python
def test_llm_judge_evaluator_exists():
    from task.evaluators.llm_judge import LLMJudgeEvaluator
    assert LLMJudgeEvaluator is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/task/test_llm_judge_interface.py -v`
Expected: FAIL because the evaluator files do not exist

**Step 3: Write minimal implementation**

- Add evaluation repository methods.
- Add base evaluator contract.
- Add first `LLM-as-Judge` evaluator skeleton.

**Step 4: Run test to verify it passes**

Run: `pytest tests/task/test_llm_judge_interface.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add data/repositories/evaluation_repository.py task/evaluators tests/task/test_llm_judge_interface.py
git commit -m "feat: add evaluation repository and evaluator interface"
```

### Task 15: Add admin APIs for evaluation task management

**Files:**
- Create: `admin/routes/evaluation_tasks.py`
- Modify: `admin/app.py`
- Create: `tests/admin/test_evaluation_tasks_api.py`

**Step 1: Write the failing test**

```python
def test_create_evaluation_task(client):
    response = client.post("/admin/evaluation-tasks", json={"name": "judge-1"})
    assert response.status_code != 404
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/admin/test_evaluation_tasks_api.py -v`
Expected: FAIL because the route does not exist

**Step 3: Write minimal implementation**

- Add create, list, detail, start, retry endpoints for evaluation tasks.
- Add score listing endpoint.

**Step 4: Run test to verify it passes**

Run: `pytest tests/admin/test_evaluation_tasks_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add admin/routes/evaluation_tasks.py admin/app.py tests/admin/test_evaluation_tasks_api.py
git commit -m "feat: add evaluation task admin api"
```

### Task 16: Implement worker evaluation processing

**Files:**
- Create: `task/jobs/evaluation_job.py`
- Create: `tests/task/test_evaluation_job.py`

**Step 1: Write the failing test**

```python
def test_evaluation_job_entrypoint_exists():
    from task.jobs.evaluation_job import run_evaluation_task
    assert run_evaluation_task is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/task/test_evaluation_job.py -v`
Expected: FAIL because the job entrypoint does not exist

**Step 3: Write minimal implementation**

- Add worker-side evaluation job.
- Load existing execution results.
- Call the selected evaluator.
- Persist `evaluation_score`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/task/test_evaluation_job.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add task/jobs/evaluation_job.py tests/task/test_evaluation_job.py
git commit -m "feat: add evaluation worker job"
```

### Task 17: Scaffold admin web frontend

**Files:**
- Create: `admin/web/package.json`
- Create: `admin/web/index.html`
- Create: `admin/web/src/main.tsx`
- Create: `admin/web/src/App.tsx`
- Create: `admin/web/src/pages/ProvidersPage.tsx`
- Create: `admin/web/src/pages/RecordsPage.tsx`
- Create: `admin/web/src/pages/ExecutionTasksPage.tsx`
- Create: `admin/web/src/pages/EvaluationTasksPage.tsx`
- Create: `admin/web/src/pages/ResultsPage.tsx`
- Test: `admin/web/src/App.test.tsx`

**Step 1: Write the failing test**

```tsx
it("renders navigation items", () => {
  render(<App />);
  expect(screen.getByText("Providers")).toBeInTheDocument();
});
```

**Step 2: Run test to verify it fails**

Run: `npm test -- --runInBand`
Expected: FAIL because the frontend is not scaffolded

**Step 3: Write minimal implementation**

- Scaffold React + Vite frontend under `admin/web`.
- Add navigation and empty pages for providers, records, execution tasks, evaluation tasks, and results.

**Step 4: Run test to verify it passes**

Run: `npm test -- --runInBand`
Expected: PASS

**Step 5: Commit**

```bash
git add admin/web
git commit -m "feat: scaffold admin web ui"
```

### Task 18: Connect admin web to provider and recording APIs

**Files:**
- Create: `admin/web/src/api/client.ts`
- Modify: `admin/web/src/pages/ProvidersPage.tsx`
- Modify: `admin/web/src/pages/RecordsPage.tsx`
- Create: `admin/web/src/components/DataTable.tsx`
- Test: `admin/web/src/pages/ProvidersPage.test.tsx`
- Test: `admin/web/src/pages/RecordsPage.test.tsx`

**Step 1: Write the failing test**

```tsx
it("loads provider data from api", async () => {
  render(<ProvidersPage />);
  expect(await screen.findByText("OpenAI")).toBeInTheDocument();
});
```

**Step 2: Run test to verify it fails**

Run: `npm test -- --runInBand`
Expected: FAIL because pages are static

**Step 3: Write minimal implementation**

- Add frontend API client.
- Connect provider list and records list pages to backend endpoints.
- Render basic tables and empty states.

**Step 4: Run test to verify it passes**

Run: `npm test -- --runInBand`
Expected: PASS

**Step 5: Commit**

```bash
git add admin/web
git commit -m "feat: connect providers and records pages"
```

### Task 19: Connect admin web to execution and evaluation task APIs

**Files:**
- Modify: `admin/web/src/pages/ExecutionTasksPage.tsx`
- Modify: `admin/web/src/pages/EvaluationTasksPage.tsx`
- Modify: `admin/web/src/pages/ResultsPage.tsx`
- Test: `admin/web/src/pages/ExecutionTasksPage.test.tsx`
- Test: `admin/web/src/pages/EvaluationTasksPage.test.tsx`

**Step 1: Write the failing test**

```tsx
it("shows execution tasks from api", async () => {
  render(<ExecutionTasksPage />);
  expect(await screen.findByText("batch-1")).toBeInTheDocument();
});
```

**Step 2: Run test to verify it fails**

Run: `npm test -- --runInBand`
Expected: FAIL because task pages are not connected

**Step 3: Write minimal implementation**

- Connect execution and evaluation pages to backend endpoints.
- Add basic task detail and result summary rendering.
- Add create-task actions from records or results pages if time permits.

**Step 4: Run test to verify it passes**

Run: `npm test -- --runInBand`
Expected: PASS

**Step 5: Commit**

```bash
git add admin/web
git commit -m "feat: connect execution and evaluation pages"
```

### Task 20: Add end-to-end smoke documentation and run verification

**Files:**
- Create: `README.md`
- Create: `docs/runbook.md`
- Modify: existing test files if needed

**Step 1: Write the failing verification checklist**

```text
- backend apps start
- migrations apply
- proxy route responds
- admin routes respond
- worker entrypoints import
```

**Step 2: Run verification to find failures**

Run: `pytest -q`
Expected: Some failures if previous tasks are incomplete

**Step 3: Write minimal implementation**

- Update `README.md` with setup and local run instructions.
- Add `docs/runbook.md` with backend, database, Redis, worker, and frontend startup commands.
- Fix any final integration issues revealed by tests.

**Step 4: Run test to verify it passes**

Run: `pytest -q`
Expected: PASS

Run: `npm test -- --runInBand`
Expected: PASS

**Step 5: Commit**

```bash
git add README.md docs/runbook.md
git commit -m "docs: add setup and verification runbook"
```
