from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "tdse-preprocessing-service"
    environment: str = "local"

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_image_uploaded: str = "image-uploaded"
    kafka_topic_image_preprocessed: str = "image-preprocessed"
    kafka_group_id: str = "preprocessing-group"
    kafka_auto_offset_reset: str = "earliest"
    kafka_poll_timeout_ms: int = 1000
    kafka_max_poll_records: int = 1
    consumer_retry_seconds: int = 5

    s3_bucket_name: str = "tdse-handwriting-images"
    aws_region: str = "us-east-1"
    aws_access_key_id: str = "minioadmin"
    aws_secret_access_key: str = "minioadmin"
    s3_endpoint_url: str = "http://localhost:9000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def kafka_bootstrap_servers_list(self) -> list[str]:
        return [
            server.strip()
            for server in self.kafka_bootstrap_servers.split(",")
            if server.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
