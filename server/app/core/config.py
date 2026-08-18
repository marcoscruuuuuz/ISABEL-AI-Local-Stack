from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    isabel_version: str = "1.0.2"
    api_token: str = "dev"
    jwt_secret: str = "change-me"
    admin_user: str = "admin"
    admin_pass: str = "change-me"

    sglang_url: str = "http://sglang:30000"
    qdrant_url: str = "http://qdrant:6333"
    redis_url: str = "redis://redis:6379/0"
    database_url: str = "postgresql+asyncpg://isabel:troque-postgres-password@postgres:5432/isabel"

    workspace_dir: str = "/workspace"
    corpus_dir: str = "/corpus"
    embed_model: str = "BAAI/bge-m3"
    llm_model: str = "local-llm"

    research_max_loops: int = 6
    research_top_k: int = 12

    agent_mode: str = "sandbox"
    allow_shell: bool = False
    max_edit_bytes: int = 2_000_000

    # Comercial
    token_price_per_1k: float = 0.02
    monthly_quota_starter: int = 500_000
    monthly_quota_pro: int = 2_000_000
    monthly_quota_enterprise: int = 10_000_000

    # Cloudflare
    cf_access_client_id: Optional[str] = None
    cf_access_client_secret: Optional[str] = None
    cf_hostname: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
