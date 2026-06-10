def test_database_settings_and_base_import():
    from data.db import get_engine
    from data.base import Base

    assert get_engine is not None
    assert Base is not None


def test_settings_reads_database_url_from_env(monkeypatch):
    from data.settings import get_settings

    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:////tmp/test-env.db")

    assert get_settings().database_url == "sqlite+pysqlite:////tmp/test-env.db"
