#!/bin/bash
set -euo pipefail

BOOTSTRAP_SERVER="${KAFKA_BOOTSTRAP_SERVERS:-kafka:9092}"

echo "Waiting for Kafka at ${BOOTSTRAP_SERVER}..."
until kafka-topics.sh --bootstrap-server "${BOOTSTRAP_SERVER}" --list >/dev/null 2>&1; do
    sleep 2
done

kafka-topics.sh --bootstrap-server "${BOOTSTRAP_SERVER}" \
    --create --if-not-exists --topic image-uploaded \
    --partitions 3 --replication-factor 1

kafka-topics.sh --bootstrap-server "${BOOTSTRAP_SERVER}" \
    --create --if-not-exists --topic image-preprocessed \
    --partitions 3 --replication-factor 1

echo "Kafka topics ready: image-uploaded, image-preprocessed"
