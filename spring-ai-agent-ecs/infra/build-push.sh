#!/bin/bash

# Spring AI MCP Agent - Build and Push Script
# Builds Docker images for AMD64/x86_64 architecture (required for ECS Fargate)
# and pushes them to Amazon ECR
# 
# IMPORTANT: This script explicitly sets the target architecture to linux/amd64
# to ensure compatibility with ECS Fargate. Without these settings, Spring Boot's
# build-image goal would build for the local machine's architecture (e.g., ARM64
# on Apple Silicon Macs), which would fail to run on ECS Fargate's AMD64 platform.

# Source common functions
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "${SCRIPT_DIR}/common.sh"

# Script configuration
COMPONENTS=("server" "client")

# Generate version tag based on git commit and timestamp
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
VERSION_TAG="${GIT_COMMIT}-${TIMESTAMP}"

# Using spin function from common.sh

echo "=================================================="
echo "Build & Push Agent Images to ECR"
echo "=================================================="
echo ""

# Change to parent directory (from infra/ to project root)
cd "$(dirname "$0")/.."

# Check required tools
if ! check_aws_cli || ! check_aws_credentials || ! check_docker; then
    exit 1
fi

# Get Maven command
MVN=$(get_maven_command)
if [ -z "$MVN" ]; then
    exit 1
fi

# Get current AWS configuration
CURRENT_REGION=$(get_aws_region)
ACCOUNT_ID=$(get_aws_account_id)

if [ -z "$ACCOUNT_ID" ]; then
    log_error "Unable to get AWS account ID"
    exit 1
fi

if [ "$CURRENT_REGION" = "not set" ]; then
    log_error "AWS region is not set"
    log_warn "Set region with: export AWS_REGION=us-east-1"
    exit 1
fi

ECR_REGISTRY=$(get_ecr_registry)

echo "📋 Configuration:"
echo "----------------"
echo "Account ID: ${ACCOUNT_ID}"
echo "Region: ${CURRENT_REGION}"
echo "ECR Registry: ${ECR_REGISTRY}"
echo "Version Tag: ${VERSION_TAG}"
echo ""

# Check if ECR repositories exist
echo "🔍 Checking ECR repositories..."
echo "------------------------------"

MISSING_REPOS=()
for component in "${COMPONENTS[@]}"; do
    repo_name="${ECR_REPO_PREFIX}-${component}"
    echo -n "Repository ${repo_name}: "
    
    if check_ecr_repository "${repo_name}" "${CURRENT_REGION}"; then
        echo -e "${GREEN}✅ Exists${NC}"
    else
        echo -e "${RED}❌ Not found${NC}"
        MISSING_REPOS+=("${repo_name}")
    fi
done

if [ ${#MISSING_REPOS[@]} -gt 0 ]; then
    echo ""
    log_error "Missing ECR repositories: ${MISSING_REPOS[*]}"
    log_warn "Run ./infra/setup-ecr.sh first to create repositories and authenticate"
    exit 1
fi

# Verify Docker authentication
echo ""
echo "🔐 Verifying Docker ECR authentication..."
echo "----------------------------------------"

echo -n "Testing ECR login... "
if docker pull "${ECR_REGISTRY}/hello-world" &>/dev/null 2>&1 || [ $? -eq 1 ]; then
    echo -e "${GREEN}✅ Authenticated${NC}"
else
    echo -e "${YELLOW}⚠️  May need authentication${NC}"
    echo "Attempting to authenticate..."
    
    if ! authenticate_docker_ecr "${CURRENT_REGION}"; then
        log_warn "Run ./infra/setup-ecr.sh to authenticate"
        exit 1
    fi
fi

# Build and push images
echo ""
echo "🏗️  Building and pushing Docker images..."
echo "========================================"

BUILD_FAILED=false

for component in "${COMPONENTS[@]}"; do
    echo ""
    echo "📦 Processing ${component}..."
    echo "----------------------------"
    
    IMAGE_NAME="${ECR_REGISTRY}/${ECR_REPO_PREFIX}-${component}"
    
    # Build the image with version tag (force AMD64 architecture for ECS Fargate)
    ${MVN} -pl ${component} spring-boot:build-image \
        -Dspring-boot.build-image.imageName="${IMAGE_NAME}:${VERSION_TAG}" \
        -Dspring-boot.build-image.builder=paketobuildpacks/builder-jammy-base:latest \
        -Dspring-boot.build-image.env.BP_JVM_VERSION=21 \
        -Dspring-boot.build-image.env.BP_BUILD_PLATFORM="linux/amd64" \
        -Dspring-boot.build-image.env.BP_RUN_PLATFORM="linux/amd64" > build-${component}.log 2>&1 &
    BUILD_PID=$!
    
    if spin $BUILD_PID "Building ${component} image"; then
        printf "\r✅ Building ${component} image... ${GREEN}Success${NC}\n"
        
        # Tag as latest for convenience
        docker tag "${IMAGE_NAME}:${VERSION_TAG}" "${IMAGE_NAME}:latest"
        
        # Push both version tag and latest
        (
            docker push "${IMAGE_NAME}:${VERSION_TAG}" && 
            docker push "${IMAGE_NAME}:latest"
        ) > push-${component}.log 2>&1 &
        PUSH_PID=$!
        
        if spin $PUSH_PID "Pushing ${component} image"; then
            printf "\r✅ Pushing ${component} image... ${GREEN}Success${NC}\n"
            echo "   Image URI: ${IMAGE_NAME}:${VERSION_TAG}"
            echo "   Also tagged as: ${IMAGE_NAME}:latest"
        else
            printf "\r❌ Pushing ${component} image... ${RED}Failed${NC}\n"
            
            # Check if the error is due to expired authorization token
            if grep -q "Your authorization token has expired" push-${component}.log 2>/dev/null; then
                echo ""
                log_error "Docker authentication token has expired!"
                log_warn "Please run: ./infra/setup-ecr.sh"
                log_info "This will re-authenticate Docker with ECR"
            else
                log_warn "Check push-${component}.log for details"
            fi
            
            BUILD_FAILED=true
        fi
    else
        printf "\r❌ Building ${component} image... ${RED}Failed${NC}\n"
        log_warn "Check build-${component}.log for details"
        BUILD_FAILED=true
    fi
done

# Cleanup log files on success
if [ "$BUILD_FAILED" = false ]; then
    echo ""
    echo "🧹 Cleaning up log files..."
    rm -f build-*.log push-*.log
fi

echo ""
echo "=================================================="

if [ "$BUILD_FAILED" = true ]; then
    log_error "Build/push failed for one or more components"
    log_warn "Check the log files for details"
    exit 1
else
    log_info "✅ All images built and pushed successfully!"
    echo ""
    echo "📝 Image Tags:"
    echo "-------------"
    for component in "${COMPONENTS[@]}"; do
        echo "${component}: ${ECR_REGISTRY}/${ECR_REPO_PREFIX}-${component}:${VERSION_TAG}"
    done
    
    # Save image tags to file for deploy script
    TAGS_FILE="$(dirname "$0")/.image-tags"
    echo "CLIENT_IMAGE_TAG=${VERSION_TAG}" > "$TAGS_FILE"
    echo "SERVER_IMAGE_TAG=${VERSION_TAG}" >> "$TAGS_FILE"
    echo "BUILD_TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$TAGS_FILE"
    echo ""
    echo "💾 Saved image tags to ${TAGS_FILE}"
    
    echo ""
    echo "📝 Next steps:"
    echo "-------------"
    echo "Update services with new images:"
    echo -e "${BLUE}./infra/deploy.sh update-services${NC}"
    echo "(This will automatically use the image tags from this build)"
fi

echo "=================================================="