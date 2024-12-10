from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(
    BaseSettings
):
    model_config = SettingsConfigDict(case_sensitive=False)
    num_thread_worker: int = 3 
    

class AppSettings(
    WorkerSettings,
    BaseSettings
):
    model_config = SettingsConfigDict(case_sensitive=False)

    title: str = "Kotaemon API"
    version: str = "0.1.0"
    api_version: str = "v1"
    cors_origins: list[str] = ["*"]
    
    @property
    def docs_path(self) -> str:
        return f"/api/{self.api_version}/docs"
    
    @property
    def redoc_path(self) -> str:
        return f"/api/{self.api_version}/redoc"
    
    @property
    def openapi_path(self) -> str:
        return f"/api/{self.api_version}/openapi.json"
    

@lru_cache(1)
def get_settings() -> AppSettings:
    return AppSettings()


settings = get_settings()
print(settings)
