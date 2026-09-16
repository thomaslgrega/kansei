from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: SecretStr
    companies: list[str] = [
        "stripe", "anthropic", "figma",
        "airtable", "discord", "gitlab", "ramp",
    ]
    request_timeout: float = 10.0


settings = Settings()