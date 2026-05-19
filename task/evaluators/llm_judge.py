import json

from api.providers.base import build_provider_adapter
from data.models import Provider
from task.evaluators.base import EvaluationResult
from task.evaluators.base import Evaluator


class LLMJudgeEvaluator(Evaluator):
    def __init__(self, *, provider: Provider, judge_model: str | None = None):
        self.provider = provider
        self.judge_model = judge_model or provider.default_model

    def evaluate(self, *, prompt: dict, candidate: dict) -> EvaluationResult:
        adapter = build_provider_adapter(self.provider)
        judge_request = {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a strict evaluator. Return JSON with keys: "
                        "score, dimension_scores, verdict, reasoning_summary."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "prompt": prompt,
                            "candidate": candidate,
                        },
                        ensure_ascii=False,
                    ),
                },
            ]
        }
        provider_response = adapter.chat_completions(judge_request, model=self.judge_model)
        if provider_response.status_code >= 400:
            return EvaluationResult(
                score=0.0,
                dimension_scores={},
                verdict="error",
                reasoning_summary=str(provider_response.body.get("error", provider_response.body)),
                raw_response=provider_response.body,
            )

        parsed = self._parse_content(provider_response.output_text)
        return EvaluationResult(
            score=float(parsed.get("score", 0.0)),
            dimension_scores=parsed.get("dimension_scores", {}),
            verdict=parsed.get("verdict"),
            reasoning_summary=parsed.get("reasoning_summary"),
            raw_response=provider_response.body,
        )

    @staticmethod
    def _parse_content(content: str | None) -> dict:
        if not content:
            return {}
        try:
            parsed = json.loads(content)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
