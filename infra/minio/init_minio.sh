#!/bin/sh
set -eu

echo "Waiting for MinIO at ${MINIO_ENDPOINT}..."
until mc alias set local "${MINIO_ENDPOINT}" "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" >/dev/null 2>&1; do
    sleep 2
done

mc mb --ignore-existing "local/${S3_BUCKET}"
echo "MinIO bucket ready: ${S3_BUCKET}"
