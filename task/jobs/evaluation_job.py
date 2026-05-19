from sqlalchemy.orm import Session

from data.repositories.provider_repository import ProviderRepository
from data.repositories.evaluation_repository import EvaluationRepository
from data.repositories.execution_repository import ExecutionRepository
from task.evaluators.llm_judge import LLMJudgeEvaluator


def run_evaluation_task(session: Session, task_id: int) -> int:
    evaluation_repository = EvaluationRepository(session)
    execution_repository = ExecutionRepository(session)
    provider_repository = ProviderRepository(session)

    task = evaluation_repository.get_task(task_id)
    if task is None:
        raise ValueError(f"evaluation task {task_id} not found")

    evaluation_repository.update_status(task_id, "running")

    results = []
    if task.source_type == "execution_task":
        results = execution_repository.list_results(task.source_ref_id)

    judge_provider = provider_repository.get_by_id(task.judge_provider_id)
    if judge_provider is None:
        raise ValueError(f"judge provider {task.judge_provider_id} not found")

    evaluator = LLMJudgeEvaluator(provider=judge_provider, judge_model=task.judge_model)
    total = len(results)
    evaluation_repository.update_progress(task_id, total=total, done=0)

    for index, result in enumerate(results, start=1):
        evaluated = evaluator.evaluate(
            prompt=result.request_body_json,
            candidate=result.response_body_json,
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

    evaluation_repository.update_status(task_id, "completed")
    return total
