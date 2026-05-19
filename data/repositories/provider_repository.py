from sqlalchemy.orm import Session

from data.models import Provider


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
    ) -> Provider:
        provider = Provider(
            name=name,
            code=code,
            provider_type=provider_type,
            base_url=base_url,
            api_key_encrypted=f"plain:{api_key}",
            default_model=default_model,
            enabled=True,
            timeout_ms=30000,
            max_retries=1,
            extra_config_json={},
        )
        self.session.add(provider)
        self.session.flush()
        self.session.refresh(provider)
        return provider

    def list_all(self) -> list[Provider]:
        return self.session.query(Provider).order_by(Provider.id.desc()).all()

    def get_by_id(self, provider_id: int) -> Provider | None:
        return self.session.get(Provider, provider_id)

    def update(
        self,
        provider_id: int,
        *,
        name: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
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
