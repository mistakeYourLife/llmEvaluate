def test_database_settings_and_base_import():
    from data.db import get_engine
    from data.base import Base

    assert get_engine is not None
    assert Base is not None
