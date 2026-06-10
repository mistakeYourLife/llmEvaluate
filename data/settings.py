from dataclasses import dataclass
import os


@dataclass(slots=True)
class Settings:
    database_url: str


def get_settings() -> Settings:
    return Settings(database_url=os.getenv("DATABASE_URL", "sqlite+pysqlite:///./llm_evaluate.db"))
