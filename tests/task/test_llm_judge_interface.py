import json

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
    result = evaluator.evaluate(
        prompt={"messages": []},
        baseline={"choices": [{"message": {"content": "old"}}]},
        candidate={"choices": [{"message": {"content": "new"}}]},
        baseline_output_text="old",
        candidate_output_text="new",
    )

    assert adapter.calls[0][1] == "task-judge-model"
    assert "可替代" in adapter.calls[0][0]["messages"][0]["content"]
    payload = json.loads(adapter.calls[0][0]["messages"][1]["content"])
    assert payload["baseline_response"] == {"choices": [{"message": {"content": "old"}}]}
    assert payload["candidate_response"] == {"choices": [{"message": {"content": "new"}}]}
    assert payload["baseline_output_text"] == "old"
    assert payload["candidate_output_text"] == "new"
    assert result.score == 7.5


def test_llm_judge_evaluator_fails_fast_on_format_mismatch(monkeypatch):
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
    result = evaluator.evaluate(
        prompt={"messages": [{"role": "user", "content": "hello"}]},
        baseline={"choices": [{"message": {"content": '{"answer":"ok"}'}}]},
        candidate={"choices": [{"message": {"content": "普通文本"}}]},
        baseline_output_text='{"answer":"ok"}',
        candidate_output_text="普通文本",
    )

    assert adapter.calls == []
    assert result.verdict == "fail"
    assert result.dimension_scores["format_consistency"] == 0.0
    assert "格式" in (result.reasoning_summary or "")
