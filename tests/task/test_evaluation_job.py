from data.base import Base
from data.db import get_engine
from data.db import get_session_factory
from data.models import EvaluationScore
from data.models import EvaluationTask
from data.models import ExecutionResult
from data.models import ExecutionTask
from data.models import Provider
from data.models import RecordedRequest
from data.models import RecordedResponse
from task.jobs.evaluation_job import run_evaluation_task


class FakeJudgeEvaluator:
    calls: list[dict] = []

    def __init__(self, *args, **kwargs):
        type(self).calls = []

    def evaluate(
        self,
        *,
        prompt: dict,
        baseline: dict | None = None,
        candidate: dict,
        baseline_output_text: str | None = None,
        candidate_output_text: str | None = None,
    ):
        type(self).calls.append(
            {
                "prompt": prompt,
                "baseline": baseline,
                "candidate": candidate,
                "baseline_output_text": baseline_output_text,
                "candidate_output_text": candidate_output_text,
            }
        )
        from task.evaluators.base import EvaluationResult

        return EvaluationResult(
            score=8.5,
            dimension_scores={
                "format_consistency": 9,
                "semantic_consistency": 8,
                "quality_parity": 8,
                "risk_control": 9,
            },
            verdict="pass",
            reasoning_summary="judge ok",
            raw_response={"ok": True},
        )


def test_evaluation_job_entrypoint_exists(tmp_path, monkeypatch):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'evaluation-job.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    session = get_session_factory(database_url)()

    judge_provider = Provider(
        name="Judge Provider",
        code="judge",
        provider_type="openai",
        base_url="https://example.com/v1",
        api_key_encrypted="plain:key",
        default_model="judge-db-model",
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
        target_provider_ids_json={},
        target_models_json={},
        status="completed",
        progress_total=1,
        progress_done=1,
        task_config_json={},
    )
    session.add(execution_task)
    session.flush()
    recorded_request = RecordedRequest(
        name="sample-1",
        provider_id=judge_provider.id,
        source_app="crm",
        request_type="chat_completions",
        model="candidate-model",
        is_stream=False,
        request_headers_json={},
        request_body_json={"messages": [{"role": "user", "content": "q"}]},
        request_text_snapshot="q",
    )
    session.add(recorded_request)
    session.flush()
    recorded_response = RecordedResponse(
        request_id=recorded_request.id,
        http_status=200,
        response_headers_json={},
        response_body_json={"choices": [{"message": {"content": "baseline a"}}]},
        response_text_snapshot="baseline a",
        first_token_latency_ms=1,
        complete_latency_ms=2,
        prompt_tokens=1,
        completion_tokens=1,
        total_tokens=2,
        tokens_per_second=1,
        error_code=None,
        error_message=None,
    )
    session.add(recorded_response)
    session.flush()
    execution_result = ExecutionResult(
        execution_task_id=execution_task.id,
        source_request_id=recorded_request.id,
        sample_id=None,
        provider_id=judge_provider.id,
        model="candidate-model",
        run_index=0,
        request_body_json={"messages": [{"role": "user", "content": "q"}]},
        response_body_json={"choices": [{"message": {"content": "a"}}]},
        output_text="a",
        http_status=200,
        success=True,
        first_token_latency_ms=1,
        complete_latency_ms=2,
        prompt_tokens=1,
        completion_tokens=1,
        total_tokens=2,
        tokens_per_second=1,
    )
    session.add(execution_result)
    session.flush()
    evaluation_task = EvaluationTask(
        name="eval-1",
        source_type="execution_task",
        source_ref_id=execution_task.id,
        evaluator_type="llm_judge",
        judge_provider_id=judge_provider.id,
        judge_model="judge-model-from-task",
        status="pending",
        progress_total=0,
        progress_done=0,
        task_config_json={},
    )
    session.add(evaluation_task)
    session.commit()

    monkeypatch.setattr("task.jobs.evaluation_job.LLMJudgeEvaluator", FakeJudgeEvaluator)
    task_id = evaluation_task.id
    session.close()

    processed = run_evaluation_task(task_id, database_url)

    session = get_session_factory(database_url)()
    stored_score = session.query(EvaluationScore).one()
    session.close()

    assert processed == 1
    assert FakeJudgeEvaluator.calls[0]["baseline"] == {"choices": [{"message": {"content": "baseline a"}}]}
    assert FakeJudgeEvaluator.calls[0]["baseline_output_text"] == "baseline a"
    assert FakeJudgeEvaluator.calls[0]["candidate_output_text"] == "a"
    assert stored_score.score == 8.5
    assert stored_score.judge_model == "judge-model-from-task"
