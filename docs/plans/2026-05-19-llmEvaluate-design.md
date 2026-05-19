# llmEvaluate Architecture Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a full LLM evaluation platform that records OpenAI-compatible traffic, replays batches against multiple providers, and evaluates execution results separately from replay.

**Architecture:** The repository is organized into four top-level modules: `api`, `admin`, `data`, and `task`. `api` accepts external OpenAI-style requests, forwards them to configured providers, and records the original request/response path as side-channel data. `admin` owns the management UI and all admin-facing APIs, including provider configuration, recorded data browsing, execution task creation, and evaluation task creation. `data` provides shared models, persistence, and repositories. `task` executes provider replay jobs and evaluation jobs as two independent flows, so replay and scoring are not tightly chained.

**Tech Stack:** Python, FastAPI, PostgreSQL, Redis, Celery or RQ, SQLAlchemy, Alembic, React.

---

## Scope

- Accept OpenAI-compatible requests in `api`.
- Record raw request and response payloads without changing the business-facing response.
- Manage providers, recordings, replay tasks, evaluation tasks, and score results in `admin`.
- Share all domain models and persistence access through `data`.
- Replay recorded data against multiple providers in `task`.
- Evaluate existing replay results independently in `task`.
- Support multiple evaluation strategies, with `LLM-as-Judge` as the first implementation.

## Module Boundaries

### `api`

- Receives external OpenAI-format traffic.
- Resolves the target provider from configuration.
- Proxies the request to the provider.
- Records request/response payloads and latency/token metrics in the background.
- Must not run evaluation logic.

### `admin`

- Exposes all management APIs for the web UI.
- Manages provider configuration.
- Browses recorded requests and responses.
- Creates and manages replay tasks.
- Creates and manages evaluation tasks.
- Hosts the web UI under the same module boundary.

### `data`

- Defines database models.
- Exposes repositories and shared schemas.
- Owns migrations and persistence conventions.
- Is reused by `api`, `admin`, and `task`.

### `task`

- Runs replay tasks that call multiple providers for a batch of recorded data.
- Runs evaluation tasks that score existing replay results.
- Does not force replay and evaluation into one coupled pipeline.
- Can replay without evaluation and evaluate without replay.

## Core Data Model

All core tables include `created_at` and `updated_at`.

### `provider`

- `id`
- `name`
- `code`
- `provider_type`
- `base_url`
- `api_key_encrypted`
- `default_model`
- `enabled`
- `timeout_ms`
- `max_retries`
- `extra_config_json`
- `created_at`
- `updated_at`

### `recorded_request`

- `id`
- `provider_id`
- `source_app`
- `request_type`
- `model`
- `is_stream`
- `request_headers_json`
- `request_body_json`
- `request_text_snapshot`
- `created_at`
- `updated_at`

### `recorded_response`

- `id`
- `request_id`
- `http_status`
- `response_headers_json`
- `response_body_json`
- `response_text_snapshot`
- `first_token_latency_ms`
- `complete_latency_ms`
- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- `tokens_per_second`
- `error_code`
- `error_message`
- `created_at`
- `updated_at`

### `eval_dataset`

- `id`
- `name`
- `description`
- `source_type`
- `filter_config_json`
- `frozen`
- `created_at`
- `updated_at`

### `eval_sample`

- `id`
- `dataset_id`
- `source_request_id`
- `sample_input_json`
- `sample_input_text`
- `expected_output_json`
- `tags_json`
- `created_at`
- `updated_at`

### `execution_task`

- `id`
- `name`
- `source_type`
- `source_ref_id`
- `target_provider_ids_json`
- `target_models_json`
- `status`
- `progress_total`
- `progress_done`
- `task_config_json`
- `created_at`
- `updated_at`

### `execution_result`

- `id`
- `execution_task_id`
- `source_request_id`
- `sample_id`
- `provider_id`
- `model`
- `run_index`
- `request_body_json`
- `response_body_json`
- `output_text`
- `http_status`
- `first_token_latency_ms`
- `complete_latency_ms`
- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- `tokens_per_second`
- `success`
- `error_code`
- `error_message`
- `created_at`
- `updated_at`

### `evaluation_task`

- `id`
- `name`
- `source_type`
- `source_ref_id`
- `evaluator_type`
- `judge_provider_id`
- `judge_model`
- `status`
- `progress_total`
- `progress_done`
- `task_config_json`
- `created_at`
- `updated_at`

### `evaluation_score`

- `id`
- `evaluation_task_id`
- `execution_result_id`
- `evaluator_type`
- `judge_provider_id`
- `judge_model`
- `score`
- `dimension_scores_json`
- `verdict`
- `reasoning_summary`
- `raw_judge_response_json`
- `created_at`
- `updated_at`

## Execution Flow

### Recording Flow in `api`

1. External business systems send OpenAI-compatible requests to `api`.
2. `api` resolves the configured provider.
3. `api` stores `recorded_request`.
4. `api` forwards the request to the provider.
5. `api` stores `recorded_response` with latency and token metrics.
6. Streamed responses stay transparent to the caller.
7. Recording failure must not block the business response path.

### Replay Flow in `task`

1. `admin` creates an `execution_task` from a recorded batch or dataset.
2. `task` reads the selected source data.
3. `task` replays each sample against multiple providers.
4. `task` stores `execution_result` for every provider and every run.
5. Replay and evaluation remain independent.

### Evaluation Flow in `task`

1. `admin` creates an `evaluation_task` from existing replay results.
2. `task` loads the selected results.
3. `task` invokes the configured evaluator.
4. `task` stores `evaluation_score`.
5. The same replay results can be scored multiple times with different evaluators.

## Evaluation Strategy

The first evaluation strategy is `LLM-as-Judge`.

- Input: source prompt, candidate output, optional reference context.
- Output: total score, dimension scores, verdict, reasoning summary, raw judge response.

First-pass dimensions:
- relevance
- correctness
- completeness
- format_following

Stability metrics:
- first token latency
- complete latency
- tokens per second
- success rate
- error rate
- score variance across repeated runs

## Admin UI

The UI lives under `admin`.

Pages:
- Provider management
- Recorded data list
- Execution task list
- Execution task detail
- Evaluation task list
- Evaluation result detail

## Acceptance Criteria

- `api` accepts OpenAI-compatible requests and forwards them to configured providers.
- Request and response payloads are recorded without breaking the caller flow.
- All core tables include `created_at` and `updated_at`.
- Providers can be created, edited, enabled, disabled, and tested from `admin`.
- Recorded data can be browsed and selected to create execution tasks.
- Execution tasks can replay data against multiple providers without triggering evaluation.
- Evaluation tasks can score existing execution results without triggering replay.
- `LLM-as-Judge` produces total score, dimension scores, and reasoning summary.
- The same execution result set can be evaluated multiple times.
- The UI can inspect providers, recordings, execution tasks, evaluation tasks, and scores.

## Notes

- Replay and evaluation are intentionally decoupled.
- The first version should optimize for correctness and traceability over horizontal scale.
- The design should stay compatible with later plugin-style expansion of provider adapters and evaluators.
