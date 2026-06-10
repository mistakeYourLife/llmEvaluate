from sqlalchemy import Boolean
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from data.base import Base
from data.models.common import TimestampMixin


class RecordedRequest(TimestampMixin, Base):
    __tablename__ = "recorded_request"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(255))
    provider_id: Mapped[int] = mapped_column(ForeignKey("provider.id"), nullable=False)
    source_app: Mapped[str | None] = mapped_column(String(255))
    request_type: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str | None] = mapped_column(String(255))
    is_stream: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    request_headers_json: Mapped[dict] = mapped_column(JSON, default=dict)
    request_body_json: Mapped[dict] = mapped_column(JSON, default=dict)
    request_text_snapshot: Mapped[str | None] = mapped_column(Text)


class RecordedResponse(TimestampMixin, Base):
    __tablename__ = "recorded_response"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("recorded_request.id"), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer)
    response_headers_json: Mapped[dict] = mapped_column(JSON, default=dict)
    response_body_json: Mapped[dict] = mapped_column(JSON, default=dict)
    response_text_snapshot: Mapped[str | None] = mapped_column(Text)
    first_token_latency_ms: Mapped[int | None] = mapped_column(Integer)
    complete_latency_ms: Mapped[int | None] = mapped_column(Integer)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    tokens_per_second: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(255))
    error_message: Mapped[str | None] = mapped_column(Text)
