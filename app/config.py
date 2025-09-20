"""Configuration management using pydantic-settings."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    # OpenAI Configuration
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o", description="OpenAI model to use")

    # Search API Configuration
    serpapi_api_key: Optional[str] = Field(None, description="SerpAPI key")
    tavily_api_key: Optional[str] = Field(None, description="Tavily API key")

    # Application Settings
    log_level: str = Field(default="INFO", description="Logging level")
    max_iterations: int = Field(default=3, description="Maximum refinement iterations")
    cache_ttl_hours: int = Field(default=24, description="Cache TTL in hours")
    data_dir: Path = Field(default=Path("./data"), description="Data directory")

    # Security
    enable_pii_redaction: bool = Field(default=True, description="Enable PII redaction")
    https_only: bool = Field(default=True, description="Enforce HTTPS for external calls")

    # LLM Settings
    temperature: float = Field(default=0.1, description="LLM temperature")
    max_tokens: int = Field(default=4000, description="Maximum tokens per request")

    def model_post_init(self, __context) -> None:
        """Create data directories if they don't exist."""
        data_path = Path(self.data_dir)
        data_path.mkdir(parents=True, exist_ok=True)
        (data_path / "runs").mkdir(exist_ok=True)
        (data_path / "cache").mkdir(exist_ok=True)


# Global settings instance
settings = Settings()
