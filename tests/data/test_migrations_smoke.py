from pathlib import Path


def test_migration_files_exist():
    assert Path("alembic.ini").exists()
    assert Path("alembic/env.py").exists()
