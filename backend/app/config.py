from pydantic_settings import BaseSettings
from pydantic import SecretStr, Field


class Settings(BaseSettings):
    openai_api_key: SecretStr = Field(alias="OPENAI_API_KEY")
    tavily_api_key: SecretStr | None = Field(default=None, alias="TAVILY_API_KEY")
    database_url: SecretStr = Field(alias="DATABASE_URL")  # e.g., postgresql+asyncpg://...
    langsmith_api_key: SecretStr | None = Field(default=None, alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="Later-MVP", alias="LANGSMITH_PROJECT")
    allowed_origins: list[str] = Field(default=["*"], alias="ALLOWED_ORIGINS")
    environment: str = Field(default="dev", alias="ENVIRONMENT")

    model_primary: str = Field(default="gpt-4o")
    model_light: str = Field(default="gpt-4o-mini")
    embeddings_model: str = Field(default="text-embedding-3-small")

    # Telegram
    telegram_bot_token: SecretStr | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_webhook_secret: str | None = Field(default=None, alias="TELEGRAM_WEBHOOK_SECRET")
    # Web base URL for deep links (fallback to allowed_origins[0] if unset)
    web_base_url: str | None = Field(default=None, alias="WEB_BASE_URL")

    # Silence "model_*" protected namespace warnings in Pydantic v2
    model_config = {
        "protected_namespaces": ("settings_",),
        "env_file": ".env",
        "extra": "ignore",
    }


settings = Settings()  # type: ignore[call-arg]

