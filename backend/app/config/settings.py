"""Application settings using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "CapsuleCorp API"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = Field(default="", repr=False)
    postgres_db: str = "capsule"
    postgres_pool_size: int = 10
    postgres_max_overflow: int = 20

    @computed_field
    @property
    def database_url(self) -> str:
        """Build async PostgreSQL connection URL."""
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.postgres_user,
                password=self.postgres_password,
                host=self.postgres_host,
                port=self.postgres_port,
                path=self.postgres_db,
            )
        )

    @computed_field
    @property
    def database_url_sync(self) -> str:
        """Build sync PostgreSQL connection URL (for migrations)."""
        return str(
            PostgresDsn.build(
                scheme="postgresql",
                username=self.postgres_user,
                password=self.postgres_password,
                host=self.postgres_host,
                port=self.postgres_port,
                path=self.postgres_db,
            )
        )

    # Security
    secret_key: str = Field(default="CHANGE_ME_IN_PRODUCTION", repr=False)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # API Key Provisioning Secret
    # Used by services (AI agents, PBX) to obtain API keys without admin credentials
    # Must be at least 32 characters. Generate with: openssl rand -hex 32
    api_key_provision_secret: str = Field(default="", repr=False)

    # KMS Keys (must match PostgreSQL app.kms_master_key)
    kms_master_key: str = Field(default="", repr=False)
    audit_hmac_key: str = Field(default="", repr=False)

    # CORS - override with CORS_ORIGINS env var (JSON array) per client deployment
    cors_origins: list[str] = [
        "http://localhost",
        "http://localhost:80",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1",
        "http://127.0.0.1:80",
    ]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "console"

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Recordings
    recording_enabled: bool = True
    recordings_base_path: str = "/opt/capsulecorp/data/recordings"
    recording_encryption_key: str = Field(default="", repr=False)
    recording_max_concurrent: int = 2
    recording_retention_days: int = 3
    recording_client_id: str = "default"

    # Ultravox / Zadarma integration
    ultravox_webhook_forward_url: str = ""
    ultravox_webhook_secret: str = Field(default="", repr=False)
    ultravox_api_key: str = Field(default="", repr=False)
    # Static API key the Ultravox agent sends as `X-API-Key` when invoking
    # outbound tool endpoints (e.g. /functions/campaign-response). Compared in
    # constant time; endpoints that depend on this MUST return 403 when empty.
    outbound_tool_api_key: str = Field(default="", repr=False)
    # Static API key for the avisos (notices) webhook endpoint. The Ultravox
    # agent sends this key when posting complaints/requests from inbound calls.
    notices_webhook_api_key: str = Field(default="", repr=False)
    # Static API key for the trips voice tool endpoint. The Ultravox agent sends
    # this key as `X-API-Key` when querying the tenant's active trips. Compared
    # in constant time; the endpoint returns 403 when empty.
    trips_tool_api_key: str = Field(default="", repr=False)
    zadarma_api_key: str = Field(default="", repr=False)
    zadarma_api_secret: str = Field(default="", repr=False)

    # Outbound calling (SIP config for Ultravox → Zadarma)
    ultravox_agent_id: str = ""
    zadarma_sip_user: str = ""
    zadarma_sip_password: str = Field(default="", repr=False)
    zadarma_sip_server: str = "sip.zadarma.com"
    zadarma_caller_id: str = ""

    # WhatsApp Business API
    whatsapp_webhook_verify_token: str = Field(default="", repr=False)
    whatsapp_app_secret: str = Field(default="", repr=False)
    whatsapp_app_id: str = Field(default="", repr=False)
    whatsapp_api_version: str = "v21.0"
    whatsapp_max_concurrent_sends: int = 5

    # Media files (WhatsApp template images, etc.)
    media_dir: str = "/opt/capsulecorp/data/media"

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        if self.environment == "production":
            if self.secret_key == "CHANGE_ME_IN_PRODUCTION":
                raise ValueError(
                    "SECRET_KEY must be changed from default in production. "
                    "Generate one with: openssl rand -hex 32"
                )
            import logging

            _log = logging.getLogger("app.config.settings")
            if not self.kms_master_key:
                _log.warning("KMS_MASTER_KEY is empty — PII encryption will fail")
            if not self.audit_hmac_key:
                _log.warning("AUDIT_HMAC_KEY is empty — audit log integrity disabled")
            if not self.recording_encryption_key and self.recording_enabled:
                _log.warning("RECORDING_ENCRYPTION_KEY is empty — recordings will fail")
        return self

    # Redis (broker for ARQ worker + SSE pub/sub)
    redis_url: str = "redis://localhost:6379"

    # Cal.com (Calendar module - direct DB access)
    calcom_db: str = "calcom"
    calcom_webhook_secret: str = Field(default="", repr=False)

    @computed_field
    @property
    def calcom_database_url(self) -> str:
        """Build async PostgreSQL connection URL for the calcom database."""
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.postgres_user,
                password=self.postgres_password,
                host=self.postgres_host,
                port=self.postgres_port,
                path=self.calcom_db,
            )
        )

    # Marketplace
    marketplace_file_path: str = "/opt/capsulecorp/marketplace.json"

    # Dashboard: recent calls display
    recent_calls_limit: int = Field(default=200, description="Max recent calls shown in dashboard")
    recent_calls_days: int = Field(default=30, description="Show calls from the last N days")

    # Newsletter / AWS SES
    aws_region: str = "eu-west-1"
    aws_access_key_id: str = Field(default="", repr=False)
    aws_secret_access_key: str = Field(default="", repr=False)
    ses_from_email: str = ""
    newsletter_app_url: str = ""

    # Newsletter — fixed per client (set in .env, not editable by client)
    nl_from_name: str = ""
    nl_from_email: str = ""
    nl_reply_to: str = ""
    nl_sending_domain: str = ""
    nl_sending_region: str = ""
    nl_ses_configuration_set: str = ""

    # Captacion (lead acquisition scraping)
    apify_api_token: str = Field(default="", repr=False)
    openai_api_key: str = Field(default="", repr=False)
    openai_model: str = "gpt-4.1-mini"
    captacion_dispatch_interval_sec: int = 100
    captacion_business_hours_start: str = "09:00"
    captacion_business_hours_end: str = "21:30"
    captacion_business_days: list[int] = [1, 2, 3, 4, 5, 6]  # ISO weekday: 1=Mon..6=Sat (no Sun)
    captacion_daily_limit: int = 50

    @field_validator("captacion_business_days", mode="before")
    @classmethod
    def _parse_business_days(cls, v: object) -> object:
        """Parse comma-separated string (e.g. '1,2,3,4,5') from .env."""
        if isinstance(v, str) and not v.startswith("["):
            return [int(x.strip()) for x in v.split(",")]
        return v

    captacion_max_concurrent_calls: int = 2
    captacion_max_retries: int = 4
    captacion_retention_days: int = 90
    captacion_email_cc: str = ""  # Secondary email recipient for OK leads

    # Margen entre fecha de publicacion del anuncio y la 1a llamada.
    # Override por tenant en organizations.settings.captacion_config.min_publication_age_days
    captacion_min_publication_age_days: int = 5
    # Dias de inactividad (sin llamadas) para reactivar lead para nuevo ciclo.
    # Override por tenant en organizations.settings.captacion_config.stale_days
    captacion_stale_days: int = 90

    # ------------------------------------------------------------------
    # BFF (Backend-for-Frontend) sessions — see f7g8h9i0j1k2 migration
    # ------------------------------------------------------------------
    # Browser cookies are opaque; tokens never leave the backend process.
    # Idle vs absolute timeouts both apply (whichever expires first wins).
    bff_session_idle_minutes: int = 30
    bff_session_absolute_hours: int = 12
    # Sliding-window write throttling: only persist last_seen_at if it has
    # been more than N seconds since the previous update. Reduces DB pressure
    # without losing meaningful expiry resolution.
    bff_session_sliding_throttle_seconds: int = 60
    # Re-auth window for sensitive operations (password change, passkey CRUD,
    # API token issuance, GDPR erase, etc.).
    bff_recent_auth_window_seconds: int = 300
    # API tokens (POST /auth/api-token) — server-to-server / CI usage.
    bff_api_token_max_ttl_hours: int = 168  # 7 days
    bff_api_token_max_active_per_user: int = 10
    # Coexistence with legacy JWT cookies. During the rollout window the
    # middleware accepts BOTH cookies and silently auto-upgrades sessions
    # that arrive via the legacy path. Set to ``false`` in Phase 1.5.
    bff_legacy_cookie_compat: bool = True

    # Email (SMTP)
    smtp_host: str = Field(default="localhost")
    smtp_port: int = Field(default=587)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="", repr=False)
    smtp_tls: bool = Field(default=True)
    smtp_from_email: str = Field(default="noreply@yourdomain.com")
    smtp_from_name: str = Field(default="Capsule Corp Dashboard")
    contact_email: str = Field(default="avisos@yourdomain.com")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
