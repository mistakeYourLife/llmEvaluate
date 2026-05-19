from dataclasses import dataclass


@dataclass(slots=True)
class EvaluationResult:
    score: float
    dimension_scores: dict
    verdict: str | None
    reasoning_summary: str | None
    raw_response: dict


class Evaluator:
    def evaluate(self, *, prompt: dict, candidate: dict) -> EvaluationResult:
        raise NotImplementedError
