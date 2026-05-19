def test_execution_job_entrypoint_exists():
    from task.jobs.execution_job import run_execution_task

    assert run_execution_task is not None
