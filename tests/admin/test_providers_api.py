from pathlib import Path

from fastapi.testclient import TestClient

from admin.app import app
from data.base import Base
from data.db import get_db_session
from data.db import get_engine
from data.db import get_session_factory
from data.models import Provider
from data.models import RecordedRequest


def test_create_provider(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'providers.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    def override_db_session():
        yield from get_db_session(database_url)

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    response = client.post(
        "/admin/providers",
        json={
            "name": "OpenAI",
            "code": "openai",
            "provider_type": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "secret",
            "default_model": "gpt-4o-mini",
            "timeout_ms": 45000,
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["timeout_ms"] == 45000
    assert response.json()["is_default"] is True


def test_update_and_disable_provider(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'providers-update.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    def override_db_session():
        yield from get_db_session(database_url)

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    create_response = client.post(
        "/admin/providers",
        json={
            "name": "OpenAI",
            "code": "openai",
            "provider_type": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "secret",
            "default_model": "gpt-4o-mini",
            "timeout_ms": 30000,
        },
    )
    client.post(
        "/admin/providers",
        json={
            "name": "Second Provider",
            "code": "second-provider",
            "provider_type": "openai",
            "base_url": "https://example.com/v1",
            "api_key": "secret-2",
            "default_model": "gpt-4.1-mini",
            "timeout_ms": 30000,
        },
    )
    provider_id = 2

    update_response = client.put(
        f"/admin/providers/{provider_id}",
        json={
            "name": "OpenAI Updated",
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4.1-mini",
            "timeout_ms": 60000,
        },
    )
    disable_response = client.post(f"/admin/providers/{provider_id}/disable")

    app.dependency_overrides.clear()

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "OpenAI Updated"
    assert update_response.json()["timeout_ms"] == 60000
    assert disable_response.status_code == 200
    assert disable_response.json()["enabled"] is False


def test_set_default_provider(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'providers-delete.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    def override_db_session():
        yield from get_db_session(database_url)

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    create_response = client.post(
        "/admin/providers",
        json={
            "name": "OpenAI",
            "code": "openai",
            "provider_type": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "secret",
            "default_model": "gpt-4o-mini",
        },
    )
    second_create_response = client.post(
        "/admin/providers",
        json={
            "name": "Second Provider",
            "code": "second-provider",
            "provider_type": "openai",
            "base_url": "https://example.com/v1",
            "api_key": "secret-2",
            "default_model": "gpt-4.1-mini",
        },
    )
    provider_id = second_create_response.json()["id"]

    set_default_response = client.post(f"/admin/providers/{provider_id}/set-default")
    list_response = client.get("/admin/providers")

    app.dependency_overrides.clear()

    assert set_default_response.status_code == 200
    assert set_default_response.json()["is_default"] is True
    provider_map = {item["code"]: item for item in list_response.json()["items"]}
    assert provider_map["second-provider"]["is_default"] is True
    assert provider_map["openai"]["is_default"] is False


def test_delete_non_default_unused_provider(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'providers-delete-non-default.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    def override_db_session():
        yield from get_db_session(database_url)

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    client.post(
        "/admin/providers",
        json={
            "name": "OpenAI",
            "code": "openai",
            "provider_type": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "secret",
            "default_model": "gpt-4o-mini",
        },
    )
    create_response = client.post(
        "/admin/providers",
        json={
            "name": "Second Provider",
            "code": "second-provider",
            "provider_type": "openai",
            "base_url": "https://example.com/v1",
            "api_key": "secret-2",
            "default_model": "gpt-4.1-mini",
        },
    )
    provider_id = create_response.json()["id"]

    delete_response = client.delete(f"/admin/providers/{provider_id}")
    list_response = client.get("/admin/providers")

    app.dependency_overrides.clear()

    assert delete_response.status_code == 204
    assert len(list_response.json()["items"]) == 1


def test_disable_default_provider_is_blocked(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'providers-disable-default.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    def override_db_session():
        yield from get_db_session(database_url)

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    create_response = client.post(
        "/admin/providers",
        json={
            "name": "OpenAI",
            "code": "openai",
            "provider_type": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "secret",
            "default_model": "gpt-4o-mini",
        },
    )
    provider_id = create_response.json()["id"]

    disable_response = client.post(f"/admin/providers/{provider_id}/disable")

    app.dependency_overrides.clear()

    assert disable_response.status_code == 409
    assert disable_response.json()["detail"] == "默认录制供应商不能直接禁用，请先切换默认供应商。"


def test_delete_default_provider_is_blocked(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'providers-delete-default.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)

    def override_db_session():
        yield from get_db_session(database_url)

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    create_response = client.post(
        "/admin/providers",
        json={
            "name": "OpenAI",
            "code": "openai",
            "provider_type": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "secret",
            "default_model": "gpt-4o-mini",
        },
    )
    provider_id = create_response.json()["id"]

    delete_response = client.delete(f"/admin/providers/{provider_id}")

    app.dependency_overrides.clear()

    assert delete_response.status_code == 409
    assert delete_response.json()["detail"] == "默认录制供应商不能直接删除，请先切换默认供应商。"


def test_delete_provider_rejects_when_recordings_exist(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'providers-delete-blocked.db'}"
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
    session.add(
        RecordedRequest(
            provider_id=provider.id,
            request_type="chat_completions",
            model="gpt-4o-mini",
            is_stream=False,
            request_headers_json={},
            request_body_json={"messages": []},
            request_text_snapshot="{}",
        )
    )
    provider_id = provider.id
    session.commit()
    session.close()

    def override_db_session():
        yield from get_db_session(database_url)

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    delete_response = client.delete(f"/admin/providers/{provider_id}")

    app.dependency_overrides.clear()

    assert delete_response.status_code == 409
    assert delete_response.json()["detail"] == "该供应商已关联 1 条录制样本，暂不允许删除。"
