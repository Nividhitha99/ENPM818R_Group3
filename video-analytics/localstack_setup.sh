#!/bin/bash
awslocal s3 mb s3://video-uploads
awslocal sqs create-queue --queue-name video-jobs
awslocal dynamodb create-table \
    --table-name video-metadata \
    --attribute-definitions AttributeName=video_id,AttributeType=S \
    --key-schema AttributeName=video_id,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5

