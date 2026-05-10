from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "tdse-results-service"
    environment: str = "local"

    jwt_secret_key: str = Field(
        default="change-this-secret-key-before-running-tdse-auth-service-prod",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"

    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    dynamodb_table_name: str = "inference-results"
    dynamodb_endpoint_url: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
