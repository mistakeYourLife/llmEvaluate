def test_execution_service_exists():
    from task.services.execution_service import ExecutionService

    assert ExecutionService is not None
