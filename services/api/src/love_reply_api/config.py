from functools import lru_cache

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
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 2_592_000
    sms_challenge_ttl_seconds: int = 300
    idempotency_ttl_seconds: int = 86_400
    idempotency_max_response_bytes: int = 1_048_576
    free_text_quota: int = 3
    quote_ttl_seconds: int = 300
    generation_event_ttl_seconds: int = 86_400
    default_model_id: str = "model_standard"
    default_style_ids: list[str] = ["warm", "humorous", "direct"]

    def assert_deployable(self) -> None:
        if self.app_env == "production" and self.jwt_signing_key.get_secret_value().startswith(
            "local-development"
        ):
            raise ValueError("JWT_SIGNING_KEY must be configured for production")


@lru_cache
def get_settings() -> Settings:
    return Settings()
