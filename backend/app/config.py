from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "APGL"
    database_url: str = "sqlite:///./backend/data/app.db"
    frontend_origin: str = "http://localhost:5173"
    session_cookie_name: str = "apgl_session"
    session_days: int = 14
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model_fast: str | None = None
    llm_model_smart: str | None = None
    llm_api_mode: str = "chat_completions"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model_fast: str = "gpt-5-mini"
    openai_model_smart: str = "gpt-5.2"
    apgl_mock_ai: bool = False
    max_upload_bytes: int = 8 * 1024 * 1024

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
