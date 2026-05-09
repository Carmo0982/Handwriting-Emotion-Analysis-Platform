#!/bin/sh
set -eu

echo "Waiting for DynamoDB Local at ${DYNAMODB_ENDPOINT}..."
until aws dynamodb list-tables --endpoint-url "${DYNAMODB_ENDPOINT}" >/dev/null 2>&1; do
    sleep 2
done

if aws dynamodb describe-table \
    --endpoint-url "${DYNAMODB_ENDPOINT}" \
    --table-name "${DYNAMODB_TABLE}" >/dev/null 2>&1; then
    echo "DynamoDB table already exists: ${DYNAMODB_TABLE}"
else
    aws dynamodb create-table \
        --endpoint-url "${DYNAMODB_ENDPOINT}" \
        --table-name "${DYNAMODB_TABLE}" \
        --attribute-definitions \
            AttributeName=tenant_id,AttributeType=S \
            AttributeName=image_id,AttributeType=S \
        --key-schema \
            AttributeName=tenant_id,KeyType=HASH \
            AttributeName=image_id,KeyType=RANGE \
        --billing-mode PAY_PER_REQUEST >/dev/null
    echo "DynamoDB table created: ${DYNAMODB_TABLE}"
fi

aws dynamodb wait table-exists \
    --endpoint-url "${DYNAMODB_ENDPOINT}" \
    --table-name "${DYNAMODB_TABLE}"

echo "DynamoDB table ready: ${DYNAMODB_TABLE}"
