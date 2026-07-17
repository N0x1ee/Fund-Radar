"""Central configuration, loaded from environment / .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "sqlite:///./fundradar.db"

    # LLM
    llm_provider: str = "mock"          # auto | gemini | groq | ollama | mock
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-lite"   # cheap, current (2.0-flash retired Jun 2026)
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"   # fast; big free daily allowance
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # Scraper
    use_playwright: bool = False        # render JS-heavy sites via headless browser

    # Email verification (Resend API). If resend_api_key is empty, verification
    # is DISABLED and the app behaves as before (no email sent, no login block).
    resend_api_key: str = ""
    email_from: str = "FundRadar <onboarding@resend.dev>"   # verified sender
    app_base_url: str = ""              # e.g. https://fundradar.onrender.com;
    #                                     blank = derive from the incoming request

    # API security / reliability
    rate_limit_per_min: int = 120       # max requests per IP per minute (0 = off)
    enable_docs: bool = True            # expose interactive /docs
    cors_allow_origins: str = ""        # comma-separated; empty = same-origin only

    # Authentication (JWT). ALWAYS override JWT_SECRET via env in production.
    jwt_secret: str = "dev-insecure-change-me"   # override via JWT_SECRET env var
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60               # access-token lifetime (minutes)
    remember_me_days: int = 30                   # "Remember me" cookie lifetime (days)
    cookie_secure: bool = False                  # True in production (HTTPS-only auth cookie)


settings = Settings()
