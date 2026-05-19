from api.providers.base import ProviderChatCompletionResult
from data.models import Provider
from task.evaluators.llm_judge import LLMJudgeEvaluator


class FakeJudgeAdapter:
    def __init__(self):
        self.calls: list[tuple[dict, str | None]] = []

    def chat_completions(self, payload: dict, model: str | None = None) -> ProviderChatCompletionResult:
        self.calls.append((payload, model))
        return ProviderChatCompletionResult(
            status_code=200,
            body={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"score": 7.5, "dimension_scores": {"relevance": 8}, '
                                '"verdict": "pass", "reasoning_summary": "ok"}'
                            )
                        }
                    }
                ]
            },
            headers={},
            first_token_latency_ms=1,
            complete_latency_ms=2,
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
            tokens_per_second=1,
            output_text='{"score": 7.5}',
        )


def test_llm_judge_evaluator_uses_model_configuration(monkeypatch):
    provider = Provider(
        id=1,
        name="Judge",
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
    adapter = FakeJudgeAdapter()
    monkeypatch.setattr("task.evaluators.llm_judge.build_provider_adapter", lambda _: adapter)

    evaluator = LLMJudgeEvaluator(provider=provider, judge_model="task-judge-model")
    result = evaluator.evaluate(prompt={"messages": []}, candidate={"choices": []})

    assert adapter.calls[0][1] == "task-judge-model"
    assert result.score == 7.5
