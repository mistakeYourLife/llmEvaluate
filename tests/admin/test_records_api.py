from pathlib import Path

from fastapi.testclient import TestClient

from admin.app import app
from data.base import Base
from data.db import get_db_session
from data.db import get_engine
from data.db import get_session_factory
from data.models import ExecutionTask
from data.models import Provider
from data.models import RecordedRequest
from data.models import RecordedResponse


def test_records_list_route_exists(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'records.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    session = get_session_factory(database_url)()
    provider = Provider(
        name="OpenAI",
        code="openai",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        api_key_encrypted="plain:secret",
        default_model="gpt-4o-mini",
        enabled=True,
        timeout_ms=30000,
        max_retries=1,
        extra_config_json={},
    )
    session.add(provider)
    session.flush()
    request = RecordedRequest(
        provider_id=provider.id,
        request_type="chat_completions",
        model="gpt-4o-mini",
        is_stream=False,
        request_headers_json={},
        request_body_json={"messages": []},
        request_text_snapshot="{}",
    )
    session.add(request)
    session.flush()
    session.add(
        RecordedResponse(
            request_id=request.id,
            http_status=200,
            response_headers_json={},
            response_body_json={"id": "resp-1"},
            response_text_snapshot="{}",
        )
    )
    session.commit()
    session.close()

    def override_db_session():
        yield from get_db_session(database_url)

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    list_response = client.get("/admin/records")
    detail_response = client.get("/admin/records/1")

    app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert len(list_response.json()["items"]) == 1
    assert list_response.json()["items"][0]["name"] == "1"
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["name"] == "1"
    assert detail_payload["request_body_json"] == {"messages": []}
    assert detail_payload["response"]["response_body_json"] == {"id": "resp-1"}
    assert detail_payload["response"]["http_status"] == 200
    assert detail_payload["created_at"]
    assert detail_payload["response"]["created_at"]


def test_delete_record_and_response(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'records-delete.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    session = get_session_factory(database_url)()
    provider = Provider(
        name="OpenAI",
        code="openai",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        api_key_encrypted="plain:secret",
        default_model="gpt-4o-mini",
        enabled=True,
        timeout_ms=30000,
        max_retries=1,
        extra_config_json={},
    )
    session.add(provider)
    session.flush()
    request = RecordedRequest(
        provider_id=provider.id,
        request_type="chat_completions",
        model="gpt-4o-mini",
        is_stream=False,
        request_headers_json={},
        request_body_json={"messages": []},
        request_text_snapshot="{}",
    )
    session.add(request)
    session.flush()
    session.add(
        RecordedResponse(
            request_id=request.id,
            http_status=200,
            response_headers_json={},
            response_body_json={"id": "resp-1"},
            response_text_snapshot="{}",
        )
    )
    record_id = request.id
    session.commit()
    session.close()

    def override_db_session():
        yield from get_db_session(database_url)

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    delete_response = client.delete(f"/admin/records/{record_id}")
    list_response = client.get("/admin/records")

    app.dependency_overrides.clear()

    assert delete_response.status_code == 204
    assert list_response.json()["items"] == []


def test_update_record_name(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'records-update.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    session = get_session_factory(database_url)()
    provider = Provider(
        name="OpenAI",
        code="openai",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        api_key_encrypted="plain:secret",
        default_model="gpt-4o-mini",
        enabled=True,
        timeout_ms=30000,
        max_retries=1,
        extra_config_json={},
    )
    session.add(provider)
    session.flush()
    request = RecordedRequest(
        provider_id=provider.id,
        request_type="chat_completions",
        model="gpt-4o-mini",
        is_stream=False,
        request_headers_json={},
        request_body_json={"messages": []},
        request_text_snapshot="{}",
    )
    session.add(request)
    session.commit()
    session.close()

    def override_db_session():
        yield from get_db_session(database_url)

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    update_response = client.put("/admin/records/1", json={"name": "客服样本-A"})
    detail_response = client.get("/admin/records/1")
    list_response = client.get("/admin/records")

    app.dependency_overrides.clear()

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "客服样本-A"
    assert detail_response.json()["name"] == "客服样本-A"
    assert list_response.json()["items"][0]["name"] == "客服样本-A"


def test_delete_record_rejects_when_execution_tasks_exist(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'records-delete-blocked.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    session = get_session_factory(database_url)()
    provider = Provider(
        name="OpenAI",
        code="openai",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        api_key_encrypted="plain:secret",
        default_model="gpt-4o-mini",
        enabled=True,
        timeout_ms=30000,
        max_retries=1,
        extra_config_json={},
    )
    session.add(provider)
    session.flush()
    request = RecordedRequest(
        provider_id=provider.id,
        request_type="chat_completions",
        model="gpt-4o-mini",
        is_stream=False,
        request_headers_json={},
        request_body_json={"messages": []},
        request_text_snapshot="{}",
    )
    session.add(request)
    session.flush()
    session.add(
        ExecutionTask(
            name="execution-1",
            source_type="recorded_request",
            source_ref_id=request.id,
            target_provider_ids_json={},
            target_models_json={},
            task_config_json={},
        )
    )
    record_id = request.id
    session.commit()
    session.close()

    def override_db_session():
        yield from get_db_session(database_url)

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    delete_response = client.delete(f"/admin/records/{record_id}")

    app.dependency_overrides.clear()

    assert delete_response.status_code == 409
    assert delete_response.json()["detail"] == "该录制样本已关联 1 条执行任务，暂不允许删除。"
