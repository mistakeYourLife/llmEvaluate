"""initial schema

Revision ID: 20260519_000001
Revises:
Create Date: 2026-05-19 14:10:00
"""

from typing import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260519_000001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "provider",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False, unique=True),
        sa.Column("provider_type", sa.String(length=100), nullable=False),
        sa.Column("base_url", sa.String(length=1024), nullable=False),
        sa.Column("api_key_encrypted", sa.String(length=4096), nullable=False),
        sa.Column("default_model", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("timeout_ms", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("extra_config_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "recorded_request",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("provider_id", sa.Integer(), sa.ForeignKey("provider.id"), nullable=False),
        sa.Column("source_app", sa.String(length=255), nullable=True),
        sa.Column("request_type", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("is_stream", sa.Boolean(), nullable=False),
        sa.Column("request_headers_json", sa.JSON(), nullable=False),
        sa.Column("request_body_json", sa.JSON(), nullable=False),
        sa.Column("request_text_snapshot", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "recorded_response",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("recorded_request.id"), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("response_headers_json", sa.JSON(), nullable=False),
        sa.Column("response_body_json", sa.JSON(), nullable=False),
        sa.Column("response_text_snapshot", sa.Text(), nullable=True),
        sa.Column("first_token_latency_ms", sa.Integer(), nullable=True),
        sa.Column("complete_latency_ms", sa.Integer(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("tokens_per_second", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "eval_dataset",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("filter_config_json", sa.JSON(), nullable=False),
        sa.Column("frozen", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "execution_task",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("source_ref_id", sa.Integer(), nullable=False),
        sa.Column("target_provider_ids_json", sa.JSON(), nullable=False),
        sa.Column("target_models_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("progress_total", sa.Integer(), nullable=False),
        sa.Column("progress_done", sa.Integer(), nullable=False),
        sa.Column("task_config_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "evaluation_task",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("source_ref_id", sa.Integer(), nullable=False),
        sa.Column("evaluator_type", sa.String(length=100), nullable=False),
        sa.Column("judge_provider_id", sa.Integer(), sa.ForeignKey("provider.id"), nullable=False),
        sa.Column("judge_model", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("progress_total", sa.Integer(), nullable=False),
        sa.Column("progress_done", sa.Integer(), nullable=False),
        sa.Column("task_config_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "eval_sample",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dataset_id", sa.Integer(), sa.ForeignKey("eval_dataset.id"), nullable=False),
        sa.Column("source_request_id", sa.Integer(), sa.ForeignKey("recorded_request.id"), nullable=True),
        sa.Column("sample_input_json", sa.JSON(), nullable=False),
        sa.Column("sample_input_text", sa.Text(), nullable=True),
        sa.Column("expected_output_json", sa.JSON(), nullable=False),
        sa.Column("tags_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "execution_result",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("execution_task_id", sa.Integer(), sa.ForeignKey("execution_task.id"), nullable=False),
        sa.Column("source_request_id", sa.Integer(), sa.ForeignKey("recorded_request.id"), nullable=True),
        sa.Column("sample_id", sa.Integer(), sa.ForeignKey("eval_sample.id"), nullable=True),
        sa.Column("provider_id", sa.Integer(), sa.ForeignKey("provider.id"), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("run_index", sa.Integer(), nullable=False),
        sa.Column("request_body_json", sa.JSON(), nullable=False),
        sa.Column("response_body_json", sa.JSON(), nullable=False),
        sa.Column("output_text", sa.Text(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("first_token_latency_ms", sa.Integer(), nullable=True),
        sa.Column("complete_latency_ms", sa.Integer(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("tokens_per_second", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "evaluation_score",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("evaluation_task_id", sa.Integer(), sa.ForeignKey("evaluation_task.id"), nullable=False),
        sa.Column("execution_result_id", sa.Integer(), sa.ForeignKey("execution_result.id"), nullable=False),
        sa.Column("evaluator_type", sa.String(length=100), nullable=False),
        sa.Column("judge_provider_id", sa.Integer(), sa.ForeignKey("provider.id"), nullable=False),
        sa.Column("judge_model", sa.String(length=255), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("dimension_scores_json", sa.JSON(), nullable=False),
        sa.Column("verdict", sa.String(length=255), nullable=True),
        sa.Column("reasoning_summary", sa.Text(), nullable=True),
        sa.Column("raw_judge_response_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("evaluation_score")
    op.drop_table("execution_result")
    op.drop_table("eval_sample")
    op.drop_table("evaluation_task")
    op.drop_table("execution_task")
    op.drop_table("eval_dataset")
    op.drop_table("recorded_response")
    op.drop_table("recorded_request")
    op.drop_table("provider")
