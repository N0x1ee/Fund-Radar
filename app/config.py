"""Central configuration, loaded from environment / .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "sqlite:///./fundradar.db"

    # LLM
    llm_provider: str = "mock"          # gemini | ollama | mock
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # Scraper
    use_playwright: bool = False        # render JS-heavy sites via headless browser

    # API security / reliability
    rate_limit_per_min: int = 120       # max requests per IP per minute (0 = off)
    enable_docs: bool = True            # expose interactive /docs
    cors_allow_origins: str = ""        # comma-separated; empty = same-origin only


settings = Settings()
