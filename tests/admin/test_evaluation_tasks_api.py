from pathlib import Path

from fastapi.testclient import TestClient

from admin.app import app
from data.base import Base
from data.db import get_db_session
from data.db import get_engine


def test_create_evaluation_task(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'evaluation-tasks.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    def override_db_session():
        yield from get_db_session(database_url)

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    response = client.post(
        "/admin/evaluation-tasks",
        json={
            "name": "judge-1",
            "source_type": "execution_task",
            "source_ref_id": 1,
            "evaluator_type": "llm_judge",
            "judge_provider_id": 1,
            "judge_model": "gpt-4o-mini",
            "task_config_json": {},
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code != 404
