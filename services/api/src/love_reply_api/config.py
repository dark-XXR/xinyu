from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    database_url: str = (
        "postgresql+asyncpg://love_reply:love_reply_dev@localhost:55432/love_reply"
    )
    redis_url: str = "redis://localhost:6379/0"
    jwt_signing_key: SecretStr = SecretStr("local-development-key-replace-before-deployment")
    jwt_issuer: str = "love-reply-api"
    admin_jwt_signing_key: SecretStr = SecretStr(
        "local-admin-signing-key-replace-before-deployment"
    )
    data_encryption_key: SecretStr = SecretStr(
        "local-data-encryption-key-replace-before-deployment"
    )
    audit_integrity_key: SecretStr = SecretStr(
        "local-audit-integrity-key-replace-before-deployment"
    )
    admin_bootstrap_login_name: str | None = None
    admin_bootstrap_password: SecretStr | None = None
    admin_bootstrap_totp_secret: SecretStr | None = None
    admin_bootstrap_display_name: str = "Platform Owner"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 2_592_000
    idempotency_ttl_seconds: int = 86_400
    idempotency_max_response_bytes: int = 1_048_576
    generation_event_ttl_seconds: int = 86_400
    referral_invite_base_url: str = "https://example.test/invite"
    audit_default_retention_days: int = 1095
    audit_sensitive_content_retention_days: int = 365
    audit_export_ttl_seconds: int = 86_400
    audit_max_export_rows: int = 5000
    # 媒体文件先落在应用管理的本地目录；接口层只暴露站内 /media 路径。
    media_storage_root: Path = Path("var/media")
    media_max_upload_bytes: int = 5_242_880
    media_max_image_pixels: int = 16_000_000

    def assert_deployable(self) -> None:
        if self.app_env == "production" and self.jwt_signing_key.get_secret_value().startswith(
            "local-development"
        ):
            raise ValueError("JWT_SIGNING_KEY must be configured for production")
        admin_signing_key = self.admin_jwt_signing_key.get_secret_value()
        if self.app_env == "production" and admin_signing_key.startswith("local-admin"):
            raise ValueError("ADMIN_JWT_SIGNING_KEY must be configured for production")
        if self.app_env == "production" and len(admin_signing_key) < 32:
            raise ValueError("ADMIN_JWT_SIGNING_KEY must be at least 32 characters")
        data_encryption_key = self.data_encryption_key.get_secret_value()
        if self.app_env == "production" and data_encryption_key.startswith("local-data"):
            raise ValueError("DATA_ENCRYPTION_KEY must be configured for production")
        if self.app_env == "production" and len(data_encryption_key) < 32:
            raise ValueError("DATA_ENCRYPTION_KEY must be at least 32 characters")
        audit_integrity_key = self.audit_integrity_key.get_secret_value()
        if self.app_env == "production" and audit_integrity_key.startswith("local-audit"):
            raise ValueError("AUDIT_INTEGRITY_KEY must be configured for production")
        if self.app_env == "production" and len(audit_integrity_key) < 32:
            raise ValueError("AUDIT_INTEGRITY_KEY must be at least 32 characters")
        if self.app_env == "production" and not self.referral_invite_base_url.startswith("https://"):
            raise ValueError("REFERRAL_INVITE_BASE_URL must use HTTPS")
        if self.media_max_upload_bytes < 1024 or self.media_max_upload_bytes > 20_971_520:
            raise ValueError("MEDIA_MAX_UPLOAD_BYTES must be between 1 KiB and 20 MiB")
        if self.media_max_image_pixels < 65_536 or self.media_max_image_pixels > 64_000_000:
            raise ValueError("MEDIA_MAX_IMAGE_PIXELS must be between 65,536 and 64,000,000")


@lru_cache
def get_settings() -> Settings:
    return Settings()
