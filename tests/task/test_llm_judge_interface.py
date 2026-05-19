def test_llm_judge_evaluator_exists():
    from task.evaluators.llm_judge import LLMJudgeEvaluator

    assert LLMJudgeEvaluator is not None
