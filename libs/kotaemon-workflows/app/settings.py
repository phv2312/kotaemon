from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict()

    TITLE: str = "Kotaemon API"
    VERSION: str = "0.1.0"

    API_V1_PREFIX: str = "/v1"

    CORS_ORIGINS: list[str] = ["*"]


settings = AppSettings()
