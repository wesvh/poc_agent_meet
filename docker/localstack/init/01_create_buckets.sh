#!/usr/bin/env bash
set -euo pipefail

echo "[localstack-init] Creating S3 buckets..."

awslocal s3 mb s3://rappi-handoff-raw     2>/dev/null || echo "bucket rappi-handoff-raw already exists"
awslocal s3 mb s3://rappi-handoff-archive 2>/dev/null || echo "bucket rappi-handoff-archive already exists"

awslocal s3api put-bucket-versioning \
    --bucket rappi-handoff-raw \
    --versioning-configuration Status=Enabled

echo "[localstack-init] S3 buckets ready."
