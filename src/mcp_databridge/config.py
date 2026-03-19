"""Application configuration via environment variables (12-factor)."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """MCP DataBridge configuration.

    All settings can be overridden via environment variables prefixed with DATABRIDGE_.
    """

    model_config = {"env_prefix": "DATABRIDGE_"}

    db_path: Path = Path("data/titanic.db")
    log_level: str = "INFO"
    max_results: int = 200
    transport: str = "stdio"
    host: str = "0.0.0.0"
    port: int = 8000
    query_timeout: int = 30


settings = Settings()
