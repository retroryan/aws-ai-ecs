#!/bin/bash

# Script to clean up all images from ECR repositories

set -e

# Configuration
ECR_REPO_PREFIX="agriculture-agent"
COMPONENTS=("main" "forecast" "historical" "agricultural")

echo "=================================================="
echo "Cleaning up ECR Images"
echo "=================================================="
echo ""

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="${AWS_REGION:-us-east-1}"

if [ -z "$ACCOUNT_ID" ]; then
    echo "Error: Unable to get AWS account ID"
    exit 1
fi

echo "Account ID: $ACCOUNT_ID"
echo "Region: $REGION"
echo ""

# Function to delete all images from a repository
delete_all_images() {
    local repo=$1
    echo "Cleaning up repository: $repo"
    
    # Get all image digests
    IMAGES=$(aws ecr list-images --repository-name "$repo" --region "$REGION" --query 'imageIds[*]' --output json 2>/dev/null || echo "[]")
    
    if [ "$IMAGES" = "[]" ]; then
        echo "  No images found in $repo"
        return
    fi
    
    # Count images
    IMAGE_COUNT=$(echo "$IMAGES" | jq '. | length')
    echo "  Found $IMAGE_COUNT images to delete"
    
    # Delete all images
    if [ "$IMAGE_COUNT" -gt 0 ]; then
        aws ecr batch-delete-image \
            --repository-name "$repo" \
            --region "$REGION" \
            --image-ids "$IMAGES" \
            --output text > /dev/null
        
        echo "  ✅ Deleted $IMAGE_COUNT images from $repo"
    fi
}

# Clean up each repository
for component in "${COMPONENTS[@]}"; do
    REPO_NAME="${ECR_REPO_PREFIX}-${component}"
    delete_all_images "$REPO_NAME"
done

echo ""
echo "✅ ECR cleanup complete!"
echo ""
echo "You can now run './infra/build-push.sh' to build fresh images"