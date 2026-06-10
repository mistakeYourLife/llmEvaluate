from pathlib import Path

from fastapi.testclient import TestClient

from admin.app import app
from api.providers.base import ProviderChatCompletionResult
from data.base import Base
from data.db import get_db_session
from data.db import get_engine
from data.db import get_session_factory
from data.models import ExecutionResult
from data.models import ExecutionTask
from data.models import EvaluationScore
from data.models import EvaluationTask
from data.models import Provider


class FakeJudgeAdapter:
    def chat_completions(self, payload: dict, model: str | None = None) -> ProviderChatCompletionResult:
        return ProviderChatCompletionResult(
            status_code=200,
            body={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"score": 9, "dimension_scores": {"relevance": 9}, '
                                '"verdict": "pass", "reasoning_summary": "ok"}'
                            )
                        }
                    }
                ]
            },
            headers={"content-type": "application/json"},
            first_token_latency_ms=3,
            complete_latency_ms=6,
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
            tokens_per_second=300.0,
            output_text='{"score": 9, "dimension_scores": {"relevance": 9}, "verdict": "pass", "reasoning_summary": "ok"}',
        )


def test_create_evaluation_task(tmp_path: Path, monkeypatch):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'evaluation-tasks.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    session = get_session_factory(database_url)()
    judge_provider = Provider(
        name="Judge",
        code="judge",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        api_key_encrypted="plain:secret",
        default_model="gpt-4o-mini",
        enabled=True,
        timeout_ms=30000,
        max_retries=1,
        extra_config_json={},
    )
    session.add(judge_provider)
    session.flush()
    execution_task = ExecutionTask(
        name="exec-1",
        source_type="recorded_request",
        source_ref_id=1,
        target_provider_ids_json={"ids": [judge_provider.id]},
        target_models_json={"models": ["gpt-4o-mini"]},
        status="completed",
        progress_total=1,
        progress_done=1,
        task_config_json={},
    )
    session.add(execution_task)
    session.flush()
    execution_result = ExecutionResult(
        execution_task_id=execution_task.id,
        source_request_id=None,
        sample_id=None,
        provider_id=judge_provider.id,
        model="gpt-4o-mini",
        run_index=0,
        request_body_json={"messages": [{"role": "user", "content": "hello"}]},
        response_body_json={"choices": [{"message": {"content": "world"}}]},
        output_text="world",
        http_status=200,
        success=True,
        first_token_latency_ms=1,
        complete_latency_ms=2,
        prompt_tokens=1,
        completion_tokens=1,
        total_tokens=2,
        tokens_per_second=100.0,
    )
    session.add(execution_result)
    session.commit()
    session.close()

    def override_db_session():
        yield from get_db_session(database_url)

    monkeypatch.setattr("task.evaluators.llm_judge.build_provider_adapter", lambda provider: FakeJudgeAdapter())
    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    response = client.post(
        "/admin/evaluation-tasks",
        json={
            "name": "judge-1",
            "source_type": "execution_task",
            "source_ref_id": 1,
            "evaluator_type": "llm_judge",
            "judge_provider_id": 1,
            "judge_model": "gpt-4o-mini",
            "task_config_json": {},
        },
    )
    task_id = response.json()["id"]
    start_response = client.post(f"/admin/evaluation-tasks/{task_id}/start")
    task_response = client.get(f"/admin/evaluation-tasks/{task_id}")
    scores_response = client.get(f"/admin/evaluation-tasks/{task_id}/scores")

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert start_response.status_code == 200
    assert start_response.json()["status"] == "running"
    assert task_response.status_code == 200
    assert task_response.json()["status"] == "completed"
    assert len(scores_response.json()["items"]) == 1


def test_delete_pending_evaluation_task(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'evaluation-task-delete.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    session = get_session_factory(database_url)()
    provider = Provider(
        name="Judge",
        code="judge",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        api_key_encrypted="plain:secret",
        default_model="gpt-4o-mini",
        enabled=True,
        timeout_ms=30000,
        max_retries=1,
        extra_config_json={},
    )
    session.add(provider)
    session.flush()
    task = EvaluationTask(
        name="judge-pending",
        source_type="execution_task",
        source_ref_id=1,
        evaluator_type="llm_judge",
        judge_provider_id=provider.id,
        judge_model="gpt-4o-mini",
        status="pending",
        progress_total=0,
        progress_done=0,
        task_config_json={},
    )
    session.add(task)
    session.commit()
    task_id = task.id
    session.close()

    def override_db_session():
        yield from get_db_session(database_url)

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    delete_response = client.delete(f"/admin/evaluation-tasks/{task_id}")
    list_response = client.get("/admin/evaluation-tasks")

    app.dependency_overrides.clear()

    assert delete_response.status_code == 204
    assert list_response.json()["items"] == []


def test_delete_completed_evaluation_task_is_blocked(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'evaluation-task-delete-blocked.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    session = get_session_factory(database_url)()
    provider = Provider(
        name="Judge",
        code="judge",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        api_key_encrypted="plain:secret",
        default_model="gpt-4o-mini",
        enabled=True,
        timeout_ms=30000,
        max_retries=1,
        extra_config_json={},
    )
    session.add(provider)
    session.flush()
    execution_task = ExecutionTask(
        name="exec-source",
        source_type="recorded_request",
        source_ref_id=1,
        target_provider_ids_json={"ids": [provider.id]},
        target_models_json={"models": ["gpt-4o-mini"]},
        status="completed",
        progress_total=1,
        progress_done=1,
        task_config_json={},
    )
    session.add(execution_task)
    session.flush()
    task = EvaluationTask(
        name="judge-completed",
        source_type="execution_task",
        source_ref_id=execution_task.id,
        evaluator_type="llm_judge",
        judge_provider_id=provider.id,
        judge_model="gpt-4o-mini",
        status="completed",
        progress_total=1,
        progress_done=1,
        task_config_json={},
    )
    session.add(task)
    session.flush()
    execution_result = ExecutionResult(
        execution_task_id=execution_task.id,
        source_request_id=None,
        sample_id=None,
        provider_id=provider.id,
        model="gpt-4o-mini",
        run_index=0,
        request_body_json={"messages": [{"role": "user", "content": "hello"}]},
        response_body_json={"choices": [{"message": {"content": "world"}}]},
        output_text="world",
        http_status=200,
        success=True,
        first_token_latency_ms=1,
        complete_latency_ms=2,
        prompt_tokens=1,
        completion_tokens=1,
        total_tokens=2,
        tokens_per_second=100.0,
    )
    session.add(execution_result)
    session.flush()
    session.add(
        EvaluationScore(
            evaluation_task_id=task.id,
            execution_result_id=execution_result.id,
            evaluator_type="llm_judge",
            judge_provider_id=provider.id,
            judge_model="gpt-4o-mini",
            score=8,
            dimension_scores_json={"relevance": 8},
            verdict="pass",
            reasoning_summary="ok",
            raw_judge_response_json={},
        )
    )
    session.commit()
    task_id = task.id
    session.close()

    def override_db_session():
        yield from get_db_session(database_url)

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    delete_response = client.delete(f"/admin/evaluation-tasks/{task_id}")

    app.dependency_overrides.clear()

    assert delete_response.status_code == 409
    assert delete_response.json()["detail"] == "该评估任务已运行或已生成评分结果，暂不允许删除。"
