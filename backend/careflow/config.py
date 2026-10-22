from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./careflow.db"
    jwt_secret: str = ""
    admin_username: str = ""
    admin_password: str = ""
    seed_demo_data: bool = False
    demo_mode: bool = True
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()

