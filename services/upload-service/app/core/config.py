from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "tdse-upload-service"
    environment: str = "local"

    jwt_secret_key: str = Field(
        default="change-this-secret-key-before-running-tdse-auth-service-prod",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"

    max_upload_size_bytes: int = 10 * 1024 * 1024
    allowed_image_content_types: str = "image/png,image/jpeg"

    s3_bucket_name: str = "tdse-handwriting-images"
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    s3_endpoint_url: str = "http://localhost:9000"

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_security_protocol: str = "PLAINTEXT"
    kafka_topic_image_uploaded: str = "image-uploaded"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def allowed_content_types(self) -> set[str]:
        return {
            content_type.strip()
            for content_type in self.allowed_image_content_types.split(",")
            if content_type.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
