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
    llm_timeout_seconds: float = 15.0
    llm_max_rounds: int = 3
    llm_max_tool_calls_per_round: int = 2
    llm_input_usd_per_1m_tokens: float = 0.0
    llm_output_usd_per_1m_tokens: float = 0.0


@lru_cache
def get_settings() -> Settings:
    return Settings()

