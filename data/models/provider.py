from sqlalchemy import Boolean
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from data.base import Base
from data.models.common import TimestampMixin


class Provider(TimestampMixin, Base):
    __tablename__ = "provider"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    provider_type: Mapped[str] = mapped_column(String(100), nullable=False, default="openai")
    base_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(String(4096), nullable=False)
    default_model: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=30000)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    extra_config_json: Mapped[dict] = mapped_column(JSON, default=dict)
