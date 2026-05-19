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


class ExecutionTask(TimestampMixin, Base):
    __tablename__ = "execution_task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_ref_id: Mapped[int] = mapped_column(Integer, nullable=False)
    target_provider_ids_json: Mapped[dict] = mapped_column(JSON, default=dict)
    target_models_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    progress_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_done: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    task_config_json: Mapped[dict] = mapped_column(JSON, default=dict)


class ExecutionResult(TimestampMixin, Base):
    __tablename__ = "execution_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_task_id: Mapped[int] = mapped_column(ForeignKey("execution_task.id"), nullable=False)
    source_request_id: Mapped[int | None] = mapped_column(ForeignKey("recorded_request.id"))
    sample_id: Mapped[int | None] = mapped_column(ForeignKey("eval_sample.id"))
    provider_id: Mapped[int] = mapped_column(ForeignKey("provider.id"), nullable=False)
    model: Mapped[str | None] = mapped_column(String(255))
    run_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_body_json: Mapped[dict] = mapped_column(JSON, default=dict)
    response_body_json: Mapped[dict] = mapped_column(JSON, default=dict)
    output_text: Mapped[str | None] = mapped_column(Text)
    http_status: Mapped[int | None] = mapped_column(Integer)
    first_token_latency_ms: Mapped[int | None] = mapped_column(Integer)
    complete_latency_ms: Mapped[int | None] = mapped_column(Integer)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    tokens_per_second: Mapped[int | None] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_code: Mapped[str | None] = mapped_column(String(255))
    error_message: Mapped[str | None] = mapped_column(Text)
