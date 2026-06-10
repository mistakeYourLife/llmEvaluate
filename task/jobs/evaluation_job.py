import logging

from data.db import get_session_factory
from data.repositories.provider_repository import ProviderRepository
from data.repositories.evaluation_repository import EvaluationRepository
from data.repositories.execution_repository import ExecutionRepository
from data.repositories.recording_repository import RecordingRepository
from task.evaluators.llm_judge import LLMJudgeEvaluator


logger = logging.getLogger(__name__)


def _commit(session) -> None:
    session.commit()
    session.expire_all()


def _mark_task_failed(session, task_id: int) -> None:
    repository = EvaluationRepository(session)
    task = repository.get_task(task_id)
    if task is None:
        return
    repository.update_status(task_id, "failed")
    _commit(session)


def run_evaluation_task(task_id: int, database_url: str | None = None) -> int:
    session_factory = get_session_factory(database_url)
    with session_factory() as session:
        try:
            return _run_evaluation_task(session, task_id)
        except Exception:
            session.rollback()
            _mark_task_failed(session, task_id)
            logger.exception("Evaluation task %s failed", task_id)
            return 0


def _run_evaluation_task(session, task_id: int) -> int:
    evaluation_repository = EvaluationRepository(session)
    execution_repository = ExecutionRepository(session)
    recording_repository = RecordingRepository(session)
    provider_repository = ProviderRepository(session)

    task = evaluation_repository.get_task(task_id)
    if task is None:
        raise ValueError(f"evaluation task {task_id} not found")

    evaluation_repository.update_status(task_id, "running")
    _commit(session)

    results = []
    if task.source_type == "execution_task":
        results = execution_repository.list_results(task.source_ref_id)

    judge_provider = provider_repository.get_by_id(task.judge_provider_id)
    if judge_provider is None:
        raise ValueError(f"judge provider {task.judge_provider_id} not found")

    evaluator = LLMJudgeEvaluator(provider=judge_provider, judge_model=task.judge_model)
    total = len(results)
    evaluation_repository.update_progress(task_id, total=total, done=0)
    _commit(session)

    for index, result in enumerate(results, start=1):
        source_request = None
        baseline_response = None
        if result.source_request_id is not None:
            recorded_pair = recording_repository.get_record(result.source_request_id)
            if recorded_pair is not None:
                source_request, baseline_response = recorded_pair

        evaluated = evaluator.evaluate(
            prompt=source_request.request_body_json if source_request is not None else result.request_body_json,
            baseline=baseline_response.response_body_json if baseline_response is not None else None,
            candidate=result.response_body_json,
            baseline_output_text=baseline_response.response_text_snapshot if baseline_response is not None else None,
            candidate_output_text=result.output_text,
        )
        evaluation_repository.create_score(
            evaluation_task_id=task.id,
            execution_result_id=result.id,
            evaluator_type=task.evaluator_type,
            judge_provider_id=task.judge_provider_id,
            judge_model=task.judge_model,
            score=evaluated.score,
            dimension_scores_json=evaluated.dimension_scores,
            verdict=evaluated.verdict,
            reasoning_summary=evaluated.reasoning_summary,
            raw_judge_response_json=evaluated.raw_response,
        )
        evaluation_repository.update_progress(task_id, total=total, done=index)
        _commit(session)

    evaluation_repository.update_status(task_id, "completed")
    _commit(session)
    return total
