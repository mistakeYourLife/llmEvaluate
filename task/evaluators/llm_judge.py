import json
from collections.abc import Mapping

from api.providers.base import build_provider_adapter
from data.models import Provider
from task.evaluators.base import EvaluationResult
from task.evaluators.base import Evaluator


dimension_keys = (
    "format_consistency",
    "semantic_consistency",
    "quality_parity",
    "risk_control",
)


class LLMJudgeEvaluator(Evaluator):
    def __init__(self, *, provider: Provider, judge_model: str | None = None):
        self.provider = provider
        self.judge_model = judge_model or provider.default_model

    def evaluate(
        self,
        *,
        prompt: dict,
        baseline: dict | None = None,
        candidate: dict,
        baseline_output_text: str | None = None,
        candidate_output_text: str | None = None,
    ) -> EvaluationResult:
        baseline_output = baseline_output_text or self._extract_output_text(baseline)
        candidate_output = candidate_output_text or self._extract_output_text(candidate)
        rule_check = self._run_format_guard(
            baseline=baseline,
            baseline_output_text=baseline_output,
            candidate=candidate,
            candidate_output_text=candidate_output,
        )
        if rule_check["blocking_issues"]:
            return EvaluationResult(
                score=0.0,
                dimension_scores=self._build_dimension_scores(format_consistency=0.0),
                verdict="fail",
                reasoning_summary=rule_check["summary"],
                raw_response={"rule_check": rule_check},
            )

        adapter = build_provider_adapter(self.provider)
        judge_request = self._build_judge_request(
            prompt=prompt,
            baseline=baseline,
            candidate=candidate,
            baseline_output_text=baseline_output,
            candidate_output_text=candidate_output,
            rule_check=rule_check,
        )
        provider_response = adapter.chat_completions(judge_request, model=self.judge_model)
        if provider_response.status_code >= 400:
            return EvaluationResult(
                score=0.0,
                dimension_scores=self._build_dimension_scores(),
                verdict="error",
                reasoning_summary=str(provider_response.body.get("error", provider_response.body)),
                raw_response={
                    "rule_check": rule_check,
                    "judge_provider_response": provider_response.body,
                },
            )

        parsed = self._parse_judge_payload(provider_response.output_text, provider_response.body)
        dimension_scores = self._normalize_dimension_scores(parsed.get("dimension_scores"))
        score = self._parse_float(parsed.get("score"))
        if score is None:
            score = self._average_dimension_score(dimension_scores)

        verdict = parsed.get("verdict")
        if verdict not in {"pass", "review", "fail", "error"}:
            verdict = None

        return EvaluationResult(
            score=score,
            dimension_scores=dimension_scores,
            verdict=verdict,
            reasoning_summary=parsed.get("reasoning_summary"),
            raw_response={
                "rule_check": rule_check,
                "judge_provider_response": provider_response.body,
                "parsed_result": parsed,
            },
        )

    def _build_judge_request(
        self,
        *,
        prompt: dict,
        baseline: dict | None,
        candidate: dict,
        baseline_output_text: str | None,
        candidate_output_text: str | None,
        rule_check: dict,
    ) -> dict:
        return {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是一个严格的业务结果评委，目标是判断候选供应商输出是否可替代基线供应商输出。"
                        "重点关注四件事：1. 格式是否兼容业务使用方式；"
                        "2. 语义是否与基线基本一致；3. 输出质量是否接近且没有明显退化；"
                        "4. 是否引入新的业务风险。忽略 id、created、usage、供应商特有元数据等非业务关键差异。"
                        "请只返回 JSON，对应字段必须包含："
                        "score, dimension_scores, verdict, reasoning_summary, blocking_issues, major_differences。"
                        "dimension_scores 必须包含：format_consistency, semantic_consistency, quality_parity, risk_control，"
                        "每个维度取值范围 0 到 10；score 取值范围 0 到 10；"
                        "verdict 只能是 pass、review、fail。"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "request_payload": prompt,
                            "baseline_response": baseline,
                            "baseline_output_text": baseline_output_text,
                            "candidate_response": candidate,
                            "candidate_output_text": candidate_output_text,
                            "rule_check": rule_check,
                        },
                        ensure_ascii=False,
                    ),
                },
            ]
        }

    @classmethod
    def _build_dimension_scores(cls, **overrides: float) -> dict:
        scores = {key: 0.0 for key in dimension_keys}
        for key, value in overrides.items():
            if key in scores:
                scores[key] = float(value)
        return scores

    @classmethod
    def _normalize_dimension_scores(cls, scores: object) -> dict:
        normalized = cls._build_dimension_scores()
        if not isinstance(scores, Mapping):
            return normalized

        for key in dimension_keys:
            value = cls._parse_float(scores.get(key))
            if value is not None:
                normalized[key] = value
        return normalized

    @staticmethod
    def _average_dimension_score(scores: dict) -> float:
        values = [value for value in scores.values() if isinstance(value, (int, float))]
        if not values:
            return 0.0
        return round(sum(values) / len(values), 2)

    @staticmethod
    def _parse_float(value: object) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _parse_judge_payload(self, output_text: str | None, body: dict | None) -> dict:
        parsed_from_output = self._parse_content(output_text)
        parsed_from_body = self._parse_content(self._extract_provider_message_content(body))
        merged = {}
        if parsed_from_body:
            merged.update(parsed_from_body)
        if parsed_from_output:
            merged.update(parsed_from_output)
        return merged

    @staticmethod
    def _extract_provider_message_content(body: dict | None) -> str | None:
        if not isinstance(body, Mapping):
            return None
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            return None
        first_choice = choices[0]
        if not isinstance(first_choice, Mapping):
            return None
        message = first_choice.get("message")
        if not isinstance(message, Mapping):
            return None
        return LLMJudgeEvaluator._normalize_message_content(message.get("content"))

    @staticmethod
    def _normalize_message_content(content: object) -> str | None:
        if isinstance(content, str):
            stripped = content.strip()
            return stripped or None
        if isinstance(content, list):
            texts: list[str] = []
            for item in content:
                if isinstance(item, Mapping) and item.get("type") == "text":
                    text = item.get("text")
                    if isinstance(text, str) and text.strip():
                        texts.append(text.strip())
            return "\n".join(texts) if texts else None
        return None

    @classmethod
    def _extract_output_text(cls, response: dict | None) -> str | None:
        if not isinstance(response, Mapping):
            return None
        return cls._extract_provider_message_content(response)

    @classmethod
    def _run_format_guard(
        cls,
        *,
        baseline: dict | None,
        baseline_output_text: str | None,
        candidate: dict,
        candidate_output_text: str | None,
    ) -> dict:
        baseline_format = cls._detect_response_format(baseline, baseline_output_text)
        candidate_format = cls._detect_response_format(candidate, candidate_output_text)
        blocking_issues: list[str] = []

        if baseline is not None and baseline_format["kind"] != "unknown" and candidate_format["kind"] == "unknown":
            blocking_issues.append("候选结果缺少可识别的业务输出结构。")

        if (
            baseline is not None
            and baseline_format["kind"] not in {"unknown", "empty_text"}
            and candidate_format["kind"] not in {"unknown", "empty_text"}
            and baseline_format["kind"] != candidate_format["kind"]
        ):
            blocking_issues.append(
                f"基线结果格式为 {baseline_format['label']}，候选结果格式为 {candidate_format['label']}，格式不兼容。"
            )

        json_shape_issue = cls._compare_json_shape(baseline_format, candidate_format)
        if json_shape_issue is not None:
            blocking_issues.append(json_shape_issue)

        summary = "格式检查通过。"
        if blocking_issues:
            summary = "；".join(blocking_issues)

        return {
            "baseline_format": baseline_format,
            "candidate_format": candidate_format,
            "blocking_issues": blocking_issues,
            "summary": summary,
        }

    @classmethod
    def _detect_response_format(cls, response: dict | None, output_text: str | None) -> dict:
        if not isinstance(response, Mapping):
            return {"kind": "unknown", "label": "未知", "json_type": None, "json_keys": []}

        choices = response.get("choices")
        if isinstance(choices, list) and choices:
            first_choice = choices[0]
            if isinstance(first_choice, Mapping):
                message = first_choice.get("message")
                if isinstance(message, Mapping):
                    tool_calls = message.get("tool_calls")
                    if isinstance(tool_calls, list) and tool_calls:
                        tool_names = []
                        for call in tool_calls:
                            if isinstance(call, Mapping):
                                function = call.get("function")
                                if isinstance(function, Mapping):
                                    name = function.get("name")
                                    if isinstance(name, str) and name.strip():
                                        tool_names.append(name.strip())
                        return {
                            "kind": "tool_calls",
                            "label": "工具调用",
                            "json_type": None,
                            "json_keys": tool_names,
                        }

                    normalized_text = cls._normalize_message_content(message.get("content")) or output_text
                    if normalized_text:
                        parsed_json = cls._parse_content(normalized_text)
                        if parsed_json:
                            return {
                                "kind": "json_text",
                                "label": "JSON 文本",
                                "json_type": type(parsed_json).__name__,
                                "json_keys": sorted(parsed_json.keys()) if isinstance(parsed_json, Mapping) else [],
                            }
                        return {
                            "kind": "plain_text",
                            "label": "纯文本",
                            "json_type": None,
                            "json_keys": [],
                        }
                    return {"kind": "empty_text", "label": "空文本", "json_type": None, "json_keys": []}

        if response.get("error") is not None:
            return {"kind": "error", "label": "错误响应", "json_type": None, "json_keys": []}

        return {"kind": "unknown", "label": "未知", "json_type": None, "json_keys": []}

    @staticmethod
    def _compare_json_shape(baseline_format: dict, candidate_format: dict) -> str | None:
        if baseline_format["kind"] != "json_text" or candidate_format["kind"] != "json_text":
            return None
        if baseline_format["json_type"] != candidate_format["json_type"]:
            return "基线结果与候选结果虽然都是 JSON 文本，但 JSON 顶层类型不一致。"

        baseline_keys = set(baseline_format.get("json_keys") or [])
        candidate_keys = set(candidate_format.get("json_keys") or [])
        if baseline_keys and candidate_keys and not baseline_keys.intersection(candidate_keys):
            return "基线结果与候选结果的 JSON 关键字段没有交集，疑似结构不兼容。"
        return None

    @staticmethod
    def _parse_content(content: str | None) -> dict:
        if not content:
            return {}
        try:
            parsed = json.loads(content)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
