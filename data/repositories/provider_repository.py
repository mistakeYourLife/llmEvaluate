from sqlalchemy.orm import Session

from data.models import EvaluationScore
from data.models import EvaluationTask
from data.models import ExecutionResult
from data.models import Provider
from data.models import RecordedRequest


class ProviderRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        *,
        name: str,
        code: str,
        provider_type: str,
        base_url: str,
        api_key: str,
        default_model: str,
        timeout_ms: int = 30000,
    ) -> Provider:
        should_be_default = self.get_default_provider() is None
        provider = Provider(
            name=name,
            code=code,
            provider_type=provider_type,
            base_url=base_url,
            api_key_encrypted=f"plain:{api_key}",
            default_model=default_model,
            enabled=True,
            is_default=should_be_default,
            timeout_ms=timeout_ms,
            max_retries=1,
            extra_config_json={},
        )
        self.session.add(provider)
        self.session.flush()
        self.session.refresh(provider)
        return provider

    def list_all(self) -> list[Provider]:
        return self.session.query(Provider).order_by(Provider.id.desc()).all()

    def get_first_enabled(self) -> Provider | None:
        return (
            self.session.query(Provider)
            .filter(Provider.enabled.is_(True))
            .order_by(Provider.id.asc())
            .first()
        )

    def get_default_provider(self) -> Provider | None:
        return (
            self.session.query(Provider)
            .filter(Provider.is_default.is_(True))
            .order_by(Provider.id.asc())
            .first()
        )

    def get_default_enabled(self) -> Provider | None:
        return (
            self.session.query(Provider)
            .filter(Provider.is_default.is_(True), Provider.enabled.is_(True))
            .order_by(Provider.id.asc())
            .first()
        )

    def get_by_id(self, provider_id: int) -> Provider | None:
        return self.session.get(Provider, provider_id)

    def update(
        self,
        provider_id: int,
        *,
        name: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
        api_key: str | None = None,
        timeout_ms: int | None = None,
    ) -> Provider | None:
        provider = self.get_by_id(provider_id)
        if provider is None:
            return None

        if name is not None:
            provider.name = name
        if base_url is not None:
            provider.base_url = base_url
        if default_model is not None:
            provider.default_model = default_model
        if api_key:
            provider.api_key_encrypted = f"plain:{api_key}"
        if timeout_ms is not None:
            provider.timeout_ms = timeout_ms

        self.session.add(provider)
        self.session.flush()
        self.session.refresh(provider)
        return provider

    def set_enabled(self, provider_id: int, enabled: bool) -> Provider | None:
        provider = self.get_by_id(provider_id)
        if provider is None:
            return None

        provider.enabled = enabled
        self.session.add(provider)
        self.session.flush()
        self.session.refresh(provider)
        return provider

    def set_default(self, provider_id: int) -> Provider | None:
        provider = self.get_by_id(provider_id)
        if provider is None:
            return None

        self.session.query(Provider).filter(Provider.id != provider_id, Provider.is_default.is_(True)).update(
            {Provider.is_default: False},
            synchronize_session=False,
        )
        provider.is_default = True
        self.session.add(provider)
        self.session.flush()
        self.session.refresh(provider)
        return provider

    def get_delete_blocker(self, provider_id: int) -> str | None:
        recorded_request_count = (
            self.session.query(RecordedRequest).filter(RecordedRequest.provider_id == provider_id).count()
        )
        if recorded_request_count > 0:
            return f"该供应商已关联 {recorded_request_count} 条录制样本，暂不允许删除。"

        execution_result_count = (
            self.session.query(ExecutionResult).filter(ExecutionResult.provider_id == provider_id).count()
        )
        if execution_result_count > 0:
            return f"该供应商已关联 {execution_result_count} 条执行结果，暂不允许删除。"

        evaluation_task_count = (
            self.session.query(EvaluationTask).filter(EvaluationTask.judge_provider_id == provider_id).count()
        )
        if evaluation_task_count > 0:
            return f"该供应商已关联 {evaluation_task_count} 条评估任务，暂不允许删除。"

        evaluation_score_count = (
            self.session.query(EvaluationScore).filter(EvaluationScore.judge_provider_id == provider_id).count()
        )
        if evaluation_score_count > 0:
            return f"该供应商已关联 {evaluation_score_count} 条评分结果，暂不允许删除。"
        return None

    def delete(self, provider_id: int) -> bool:
        provider = self.get_by_id(provider_id)
        if provider is None:
            return False

        self.session.delete(provider)
        self.session.flush()
        return True
