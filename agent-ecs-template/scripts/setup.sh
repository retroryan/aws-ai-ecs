#!/bin/bash

# Initial setup script for local development

echo "Setting up local development environment..."

# Run AWS setup from infra directory
./infra/aws-setup.sh

# Copy bedrock.env to server/.env if it doesn't exist
if [ -f bedrock.env ] && [ ! -f server/.env ]; then
    cp bedrock.env server/.env
    echo "✅ Copied bedrock.env to server/.env"
fi

echo ""
echo "Setup complete! You can now run:"
echo "  ./scripts/start.sh - To start the services"