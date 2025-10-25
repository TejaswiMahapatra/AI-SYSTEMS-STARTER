"""
Configuration management using Pydantic Settings.

Copyright 2025 Tejaswi Mahapatra
Licensed under the Apache License, Version 2.0
"""

from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = "AI Systems Starter"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    workers: int = 1

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "ai_systems"

    @property
    def database_url(self) -> str:
        """Construct async PostgreSQL URL."""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def database_url_sync(self) -> str:
        """Construct sync PostgreSQL URL for Alembic migrations."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # Weaviate
    weaviate_url: str = "http://localhost:8080"
    weaviate_api_key: Optional[str] = None

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket: str = "pdf-uploads"

    # LLM Provider
    llm_provider: Literal["ollama", "openai", "anthropic"] = "ollama"

    # Ollama
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_temperature: float = 0.7
    ollama_timeout: int = 300

    # OpenAI (Optional)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"
    openai_temperature: float = 0.7

    # Anthropic (Optional)
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-sonnet-20240229"
    anthropic_temperature: float = 0.7

    # Embeddings Provider
    embedding_provider: Literal["local", "openai"] = "local"

    # Local Embeddings
    local_embedding_model: str = "all-MiniLM-L6-v2"
    local_embedding_device: str = "cpu"  # or "cuda" if GPU available

    # OpenAI Embeddings (Optional)
    openai_embedding_model: str = "text-embedding-3-small"

    # PDF Processing
    pdf_chunk_size: int = 1000
    pdf_chunk_overlap: int = 200
    pdf_max_file_size: int = 50 * 1024 * 1024  # 50 MB

    # Vector Database
    vector_collection_name: str = "documents"
    vector_similarity_top_k: int = 5

    # Observability
    enable_langsmith: bool = False
    langsmith_api_key: Optional[str] = None
    langsmith_project: str = "ai-systems-starter"

    enable_prometheus: bool = True
    prometheus_port: int = 9090

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: str = "json"  # or "text"

    # Security
    secret_key: str = "change-this-in-production-use-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds


# Global settings instance
settings = Settings()


# Validate critical settings on startup
def validate_settings():
    """Validate critical configuration settings."""
    errors = []

    # Check LLM provider configuration
    if settings.llm_provider == "openai" and not settings.openai_api_key:
        errors.append("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

    if settings.llm_provider == "anthropic" and not settings.anthropic_api_key:
        errors.append("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")

    # Check embedding provider configuration
    if settings.embedding_provider == "openai" and not settings.openai_api_key:
        errors.append("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")

    # Check LangSmith configuration
    if settings.enable_langsmith and not settings.langsmith_api_key:
        errors.append("LANGSMITH_API_KEY is required when ENABLE_LANGSMITH=true")

    # Check production settings
    if settings.environment == "production":
        if settings.secret_key == "change-this-in-production-use-openssl-rand-hex-32":
            errors.append("SECRET_KEY must be changed in production")
        if settings.debug:
            errors.append("DEBUG should be False in production")

    if errors:
        raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))


if __name__ == "__main__":
    # Test configuration loading
    print(f"App: {settings.app_name} v{settings.app_version}")
    print(f"Environment: {settings.environment}")
    print(f"Database: {settings.database_url}")
    print(f"Redis: {settings.redis_url}")
    print(f"LLM Provider: {settings.llm_provider}")
    print(f"Embedding Provider: {settings.embedding_provider}")

    try:
        validate_settings()
        print("\nConfiguration is valid!")
    except ValueError as e:
        print(f"\n{e}")
