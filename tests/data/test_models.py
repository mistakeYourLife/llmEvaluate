def test_all_core_models_have_audit_fields():
    from data.models import ExecutionTask
    from data.models import Provider
    from data.models import RecordedRequest

    for model in [Provider, RecordedRequest, ExecutionTask]:
        assert hasattr(model, "created_at")
        assert hasattr(model, "updated_at")
