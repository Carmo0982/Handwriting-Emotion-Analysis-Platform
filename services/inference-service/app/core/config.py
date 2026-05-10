from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "tdse-inference-service"
    environment: str = "local"

    model_path: str = "models/emotion_classifier.pt"
    model_cache_dir: str = "/tmp/tdse-models"
    device: str = "cpu"
    use_dummy_model_if_missing: bool = True

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_security_protocol: str = "PLAINTEXT"
    kafka_topic_image_preprocessed: str = "image-preprocessed"
    kafka_group_id: str = "inference-group"
    kafka_auto_offset_reset: str = "earliest"
    kafka_poll_timeout_ms: int = 1000
    kafka_max_poll_records: int = 1
    consumer_retry_seconds: int = 5

    s3_bucket_name: str = "tdse-handwriting-images"
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    s3_endpoint_url: str = ""

    dynamodb_table_name: str = "inference-results"
    dynamodb_endpoint_url: str = ""

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

    @property
    def model_file_exists(self) -> bool:
        if self.model_path.startswith("s3://"):
            return True
        return Path(self.model_path).exists()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
