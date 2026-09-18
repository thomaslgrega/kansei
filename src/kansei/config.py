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
    openai_model: str = "gpt-5.6-luna"
    llm_max_postings: int = 300
    llm_concurrency: int = 8
    llm_timeout: float = 60.0


settings = Settings()
