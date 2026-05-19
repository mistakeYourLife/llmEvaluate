from dataclasses import dataclass
import os


@dataclass(slots=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite+pysqlite:///./llm_evaluate.db")


def get_settings() -> Settings:
    return Settings()
