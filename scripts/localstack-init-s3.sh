#!/bin/sh

# Initialize the mock S3 bucket for LocalStack once the service is ready.
set -e

BUCKET_NAME="smartfridge-snapshots"

awslocal s3 mb "s3://${BUCKET_NAME}" 2>/dev/null || true
