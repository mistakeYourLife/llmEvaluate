from api.providers.base import ProviderChatCompletionResult
from data.base import Base
from data.db import get_engine
from data.db import get_session_factory
from data.models import ExecutionResult
from data.models import ExecutionTask
from data.models import Provider
from data.models import RecordedRequest
from task.jobs.execution_job import run_execution_task


class FakeReplayAdapter:
    def __init__(self):
        self.calls: list[tuple[dict, str | None]] = []

    def chat_completions(self, payload: dict, model: str | None = None) -> ProviderChatCompletionResult:
        self.calls.append((payload, model))
        return ProviderChatCompletionResult(
            status_code=200,
            body={
                "id": "replay-result",
                "choices": [{"message": {"content": "replay-ok"}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
            },
            headers={"content-type": "application/json"},
            first_token_latency_ms=8,
            complete_latency_ms=20,
            prompt_tokens=3,
            completion_tokens=2,
            total_tokens=5,
            tokens_per_second=100.0,
            output_text="replay-ok",
        )


def test_execution_job_entrypoint_exists(tmp_path, monkeypatch):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'execution-job.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    session = get_session_factory(database_url)()

    provider = Provider(
        name="Replay Provider",
        code="replay",
        provider_type="openai",
        base_url="https://example.com/v1",
        api_key_encrypted="plain:key",
        default_model="db-replay-model",
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
        model=None,
        is_stream=False,
        request_headers_json={},
        request_body_json={"messages": [{"role": "user", "content": "hi"}]},
        request_text_snapshot="hi",
    )
    session.add(request)
    session.flush()
    task = ExecutionTask(
        name="task-1",
        source_type="recorded_request",
        source_ref_id=request.id,
        target_provider_ids_json={"ids": [provider.id]},
        target_models_json={},
        status="pending",
        progress_total=0,
        progress_done=0,
        task_config_json={"run_count": 3},
    )
    session.add(task)
    session.commit()
    task_id = task.id
    session.close()

    adapter = FakeReplayAdapter()
    monkeypatch.setattr("task.jobs.execution_job.build_provider_adapter", lambda provider: adapter)

    processed = run_execution_task(task_id, database_url)

    session = get_session_factory(database_url)()
    stored_results = session.query(ExecutionResult).order_by(ExecutionResult.id.asc()).all()
    stored_task = session.get(ExecutionTask, task_id)
    session.close()

    assert processed == 3
    assert len(adapter.calls) == 3
    assert adapter.calls[0][1] == "db-replay-model"
    assert [item.run_index for item in stored_results] == [0, 1, 2]
    assert all(item.model == "db-replay-model" for item in stored_results)
    assert all(item.request_body_json["model"] == "db-replay-model" for item in stored_results)
    assert all(item.output_text == "replay-ok" for item in stored_results)
    assert stored_task is not None
    assert stored_task.progress_total == 3
    assert stored_task.progress_done == 3
