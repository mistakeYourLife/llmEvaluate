from task.evaluators.base import EvaluationResult
from task.evaluators.base import Evaluator


class LLMJudgeEvaluator(Evaluator):
    def evaluate(self, *, prompt: dict, candidate: dict) -> EvaluationResult:
        return EvaluationResult(
            score=0.0,
            dimension_scores={
                "relevance": 0.0,
                "correctness": 0.0,
                "completeness": 0.0,
                "format_following": 0.0,
            },
            verdict="pending",
            reasoning_summary="stub evaluator",
            raw_response={"prompt": prompt, "candidate": candidate},
        )
