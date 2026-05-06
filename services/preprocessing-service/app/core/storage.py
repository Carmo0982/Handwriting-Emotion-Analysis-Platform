from functools import lru_cache
from typing import Any

from app.core.config import settings


@lru_cache
def get_s3_client() -> Any:
    import boto3

    client_options: dict[str, Any] = {
        "service_name": "s3",
        "region_name": settings.aws_region,
    }
    if settings.s3_endpoint_url:
        client_options["endpoint_url"] = settings.s3_endpoint_url
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        client_options["aws_access_key_id"] = settings.aws_access_key_id
        client_options["aws_secret_access_key"] = settings.aws_secret_access_key

    return boto3.client(**client_options)


def download_from_s3(key: str) -> bytes:
    response = get_s3_client().get_object(Bucket=settings.s3_bucket_name, Key=key)
    return response["Body"].read()


def upload_to_s3(file_bytes: bytes, key: str) -> str:
    get_s3_client().put_object(
        Bucket=settings.s3_bucket_name,
        Key=key,
        Body=file_bytes,
        ContentType="image/png",
    )
    return key
