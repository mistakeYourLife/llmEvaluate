from pathlib import Path

from fastapi.testclient import TestClient

from admin.app import app
from api.providers.base import ProviderChatCompletionResult
from data.base import Base
from data.db import get_db_session
from data.db import get_engine
from data.db import get_session_factory
from data.models import ExecutionTask
from data.models import Provider
from data.models import RecordedRequest


class FakeExecutionAdapter:
    def chat_completions(self, payload: dict, model: str | None = None) -> ProviderChatCompletionResult:
        return ProviderChatCompletionResult(
            status_code=200,
            body={
                "id": "exec-1",
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
            },
            headers={"content-type": "application/json"},
            first_token_latency_ms=5,
            complete_latency_ms=10,
            prompt_tokens=1,
            completion_tokens=2,
            total_tokens=3,
            tokens_per_second=200.0,
            output_text="ok",
        )


def test_create_execution_task(tmp_path: Path, monkeypatch):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'execution-tasks.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    session = get_session_factory(database_url)()
    provider = Provider(
        name="OpenAI",
        code="openai",
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
    request = RecordedRequest(
        provider_id=provider.id,
        request_type="chat_completions",
        model="gpt-4o-mini",
        is_stream=False,
        request_headers_json={},
        request_body_json={"messages": [{"role": "user", "content": "hi"}]},
        request_text_snapshot="hi",
    )
    session.add(request)
    session.commit()
    session.close()

    def override_db_session():
        yield from get_db_session(database_url)

    monkeypatch.setattr("task.jobs.execution_job.build_provider_adapter", lambda provider: FakeExecutionAdapter())
    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    response = client.post(
        "/admin/execution-tasks",
        json={
            "name": "batch-1",
            "source_type": "recorded_request",
            "source_ref_id": 1,
            "target_provider_ids_json": {"ids": [1]},
            "target_models_json": {"models": ["gpt-4o-mini"]},
            "task_config_json": {"run_count": 2},
        },
    )
    list_response = client.get("/admin/execution-tasks")
    task_id = response.json()["id"]
    start_response = client.post(f"/admin/execution-tasks/{task_id}/start")
    task_response = client.get(f"/admin/execution-tasks/{task_id}")
    results_response = client.get(f"/admin/execution-tasks/{task_id}/results")
    result_id = results_response.json()["items"][0]["id"]
    detail_response = client.get(f"/admin/execution-tasks/{task_id}/results/{result_id}")

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["target_provider_ids_json"] == {"ids": [1]}
    assert response.json()["target_models_json"] == {"models": ["gpt-4o-mini"]}
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["target_provider_ids_json"] == {"ids": [1]}
    assert list_response.json()["items"][0]["target_models_json"] == {"models": ["gpt-4o-mini"]}
    assert start_response.status_code == 200
    assert start_response.json()["status"] == "running"
    assert task_response.status_code == 200
    assert task_response.json()["status"] == "completed"
    assert task_response.json()["progress_total"] == 2
    assert task_response.json()["progress_done"] == 2
    assert len(results_response.json()["items"]) == 2
    assert [item["run_index"] for item in results_response.json()["items"]] == [0, 1]
    assert results_response.json()["items"][0]["first_token_latency_ms"] == 5
    assert results_response.json()["items"][0]["complete_latency_ms"] == 10
    assert results_response.json()["items"][0]["prompt_tokens"] == 1
    assert results_response.json()["items"][0]["completion_tokens"] == 2
    assert results_response.json()["items"][0]["total_tokens"] == 3
    assert results_response.json()["items"][0]["tokens_per_second"] == 200
    assert detail_response.status_code == 200
    assert detail_response.json()["run_index"] == 0
    assert detail_response.json()["request_body_json"]["model"] == "gpt-4o-mini"
    assert detail_response.json()["response_body_json"]["id"] == "exec-1"
    assert detail_response.json()["output_text"] == "ok"


def test_update_execution_task_name(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'execution-task-update.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    session = get_session_factory(database_url)()
    task = ExecutionTask(
        name="batch-1",
        source_type="recorded_request",
        source_ref_id=1,
        target_provider_ids_json={"ids": [1]},
        target_models_json={"models": ["gpt-4o-mini"]},
        status="pending",
        progress_total=0,
        progress_done=0,
        task_config_json={"run_count": 1},
    )
    session.add(task)
    session.commit()
    task_id = task.id
    session.close()

    def override_db_session():
        yield from get_db_session(database_url)

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    update_response = client.put(f"/admin/execution-tasks/{task_id}", json={"name": "客服问答批次"})
    detail_response = client.get(f"/admin/execution-tasks/{task_id}")

    app.dependency_overrides.clear()

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "客服问答批次"
    assert detail_response.status_code == 200
    assert detail_response.json()["name"] == "客服问答批次"
