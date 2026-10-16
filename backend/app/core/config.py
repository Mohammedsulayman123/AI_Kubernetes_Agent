from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    openrouter_api_key: str = ""
    openrouter_model: str = ""
    kubeconfig_path: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]
    insforge_base_url: str = "https://4fwr5aay.us-east.insforge.app"
    insforge_anon_key: str = "anon_c9d15cd959cd12c8977b06e38910210faf38037b607f8990378411f6c7fa682c"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
