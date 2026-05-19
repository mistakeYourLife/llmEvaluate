def test_evaluation_job_entrypoint_exists():
    from task.jobs.evaluation_job import run_evaluation_task

    assert run_evaluation_task is not None
