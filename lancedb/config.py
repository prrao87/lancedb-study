from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            ".env",
            str(Path(__file__).resolve().parent / ".env"),
        ),
        extra="allow",
    )
    lancedb_dir: str = "winemag"
    embedding_model_checkpoint: str = "nomic-ai/modernbert-embed-base"
