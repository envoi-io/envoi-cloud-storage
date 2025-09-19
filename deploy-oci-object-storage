#!/bin/bash

# Define variables
COMPARTMENT_ID=""
BUCKET_NAME="my-new-bucket-$(date +%Y%m%d%H%M%S)"
BUCKET_NAMESPACE=$(oci os ns get --query 'data' --raw-output)

# Create the Object Storage bucket
echo "Creating Object Storage bucket..."
oci os bucket create \
    --compartment-id "$COMPARTMENT_ID" \
    --name "$BUCKET_NAME"

echo "Bucket '$BUCKET_NAME' created in namespace '$BUCKET_NAMESPACE'."
