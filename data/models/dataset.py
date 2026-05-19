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


class EvalDataset(TimestampMixin, Base):
    __tablename__ = "eval_dataset"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    filter_config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    frozen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class EvalSample(TimestampMixin, Base):
    __tablename__ = "eval_sample"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("eval_dataset.id"), nullable=False)
    source_request_id: Mapped[int | None] = mapped_column(ForeignKey("recorded_request.id"))
    sample_input_json: Mapped[dict] = mapped_column(JSON, default=dict)
    sample_input_text: Mapped[str | None] = mapped_column(Text)
    expected_output_json: Mapped[dict] = mapped_column(JSON, default=dict)
    tags_json: Mapped[dict] = mapped_column(JSON, default=dict)
