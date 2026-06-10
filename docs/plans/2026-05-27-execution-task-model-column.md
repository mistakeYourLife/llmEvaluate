# Execution Task Model Column Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Show the configured execution model set in the execution task list, using override models first and falling back to provider default models when no override is configured.

**Architecture:** Extend the execution task admin response to include `target_provider_ids_json` and `target_models_json`, then let the admin web derive a human-readable model string from the already loaded provider list. Keep the execution job behavior unchanged.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, React, TypeScript, Vitest.

---

### Task 1: Define the backend response contract in tests

**Files:**
- Modify: `tests/admin/test_execution_tasks_api.py`

**Steps:**
- Assert execution task responses include `target_provider_ids_json` and `target_models_json`.
- Verify the create response echoes the configured model override.

### Task 2: Define the admin web display behavior in tests

**Files:**
- Modify: `admin/web/src/App.test.tsx`

**Steps:**
- Expect a new `执行模型` column in the execution task table.
- Verify tasks with override models show those configured models.
- Verify tasks without overrides show default models derived from selected providers.

### Task 3: Implement backend response changes

**Files:**
- Modify: `admin/schemas.py`
- Modify: `admin/routes/execution_tasks.py`

**Steps:**
- Add the two JSON fields to `ExecutionTaskResponse`.
- Return them from the execution task route mapping helper.

### Task 4: Implement frontend rendering

**Files:**
- Modify: `admin/web/src/api/client.ts`
- Modify: `admin/web/src/App.tsx`

**Steps:**
- Extend `ExecutionTask` type with the two JSON fields.
- Add a helper to derive the display string for `执行模型`.
- Render the new column in the execution task table and keep fallbacks stable.

### Task 5: Run regressions

**Steps:**
- Run: `.venv/bin/pytest -q tests/admin/test_execution_tasks_api.py`
- Run: `npm test -- --run App.test.tsx`
- Run: `npm run build`
