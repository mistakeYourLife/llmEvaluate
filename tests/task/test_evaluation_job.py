from data.base import Base
from data.db import get_engine
from data.db import get_session_factory
from data.models import EvaluationScore
from data.models import EvaluationTask
from data.models import ExecutionResult
from data.models import ExecutionTask
from data.models import Provider
from task.jobs.evaluation_job import run_evaluation_task


class FakeJudgeEvaluator:
    def __init__(self, *args, **kwargs):
        self.calls: list[tuple[dict, dict]] = []

    def evaluate(self, *, prompt: dict, candidate: dict):
        self.calls.append((prompt, candidate))
        from task.evaluators.base import EvaluationResult

        return EvaluationResult(
            score=8.5,
            dimension_scores={
                "relevance": 9,
                "correctness": 8,
                "completeness": 8,
                "format_following": 9,
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
    execution_result = ExecutionResult(
        execution_task_id=execution_task.id,
        source_request_id=None,
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
    processed = run_evaluation_task(session, evaluation_task.id)
    stored_score = session.query(EvaluationScore).one()
    session.close()

    assert processed == 1
    assert stored_score.score == 8.5
    assert stored_score.judge_model == "judge-model-from-task"
