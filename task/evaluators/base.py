from dataclasses import dataclass


@dataclass(slots=True)
class EvaluationResult:
    score: float
    dimension_scores: dict
    verdict: str | None
    reasoning_summary: str | None
    raw_response: dict


class Evaluator:
    def evaluate(
        self,
        *,
        prompt: dict,
        baseline: dict | None = None,
        candidate: dict,
        baseline_output_text: str | None = None,
        candidate_output_text: str | None = None,
    ) -> EvaluationResult:
        raise NotImplementedError
