from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from data.base import Base
from data.models.common import TimestampMixin


class EvaluationTask(TimestampMixin, Base):
    __tablename__ = "evaluation_task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_ref_id: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluator_type: Mapped[str] = mapped_column(String(100), nullable=False)
    judge_provider_id: Mapped[int] = mapped_column(ForeignKey("provider.id"), nullable=False)
    judge_model: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    progress_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_done: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    task_config_json: Mapped[dict] = mapped_column(JSON, default=dict)


class EvaluationScore(TimestampMixin, Base):
    __tablename__ = "evaluation_score"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_task_id: Mapped[int] = mapped_column(ForeignKey("evaluation_task.id"), nullable=False)
    execution_result_id: Mapped[int] = mapped_column(ForeignKey("execution_result.id"), nullable=False)
    evaluator_type: Mapped[str] = mapped_column(String(100), nullable=False)
    judge_provider_id: Mapped[int] = mapped_column(ForeignKey("provider.id"), nullable=False)
    judge_model: Mapped[str] = mapped_column(String(255), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    dimension_scores_json: Mapped[dict] = mapped_column(JSON, default=dict)
    verdict: Mapped[str | None] = mapped_column(String(255))
    reasoning_summary: Mapped[str | None] = mapped_column(Text)
    raw_judge_response_json: Mapped[dict] = mapped_column(JSON, default=dict)
