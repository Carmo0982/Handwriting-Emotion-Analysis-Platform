#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <aws-account-id> <aws-region> [image-tag]" >&2
  exit 1
fi

AWS_ACCOUNT_ID="$1"
AWS_REGION="$2"
IMAGE_TAG="${3:-v1.0.0}"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

SERVICES=(
  "auth-service:services/auth-service:services/auth-service/Dockerfile"
  "upload-service:services/upload-service:services/upload-service/Dockerfile"
  "preprocessing-service:services/preprocessing-service:services/preprocessing-service/Dockerfile"
  "results-service:services/results-service:services/results-service/Dockerfile"
  "tenant-service:services/tenant-service:services/tenant-service/Dockerfile"
)

aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin "${ECR_REGISTRY}"

for service_spec in "${SERVICES[@]}"; do
  IFS=":" read -r service_name context dockerfile <<< "${service_spec}"
  repository="tdse/${service_name}"
  image="${ECR_REGISTRY}/${repository}:${IMAGE_TAG}"

  if [[ ! -f "${dockerfile}" ]]; then
    echo "Skipping ${service_name}: ${dockerfile} does not exist yet."
    continue
  fi

  aws ecr describe-repositories \
    --region "${AWS_REGION}" \
    --repository-names "${repository}" >/dev/null 2>&1 \
    || aws ecr create-repository \
      --region "${AWS_REGION}" \
      --repository-name "${repository}" >/dev/null

  docker build -f "${dockerfile}" -t "${image}" "${context}"
  docker push "${image}"
done

inference_repository="tdse/inference-service"
inference_image="${ECR_REGISTRY}/${inference_repository}:${IMAGE_TAG}"

aws ecr describe-repositories \
  --region "${AWS_REGION}" \
  --repository-names "${inference_repository}" >/dev/null 2>&1 \
  || aws ecr create-repository \
    --region "${AWS_REGION}" \
    --repository-name "${inference_repository}" >/dev/null

docker build \
  -f services/inference-service/Dockerfile \
  --build-arg BASE_IMAGE=pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime \
  -t "${inference_image}" \
  .
docker push "${inference_image}"
