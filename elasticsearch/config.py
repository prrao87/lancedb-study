from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
    )

    elastic_user: str
    elastic_password: str = ""
    stack_version: str
    elastic_index_alias: str
    elastic_port: int
    kibana_port: int
    elastic_url: str
    elastic_service: str
    embedding_model_checkpoint: str
