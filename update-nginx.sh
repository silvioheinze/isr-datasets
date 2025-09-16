#!/bin/bash

# Script to update nginx configuration for large file uploads
# This script rebuilds and pushes the nginx image with updated settings

set -e

echo "🔧 Updating Nginx Configuration for Large File Uploads"
echo "====================================================="

# Check if we're in the right directory
if [ ! -f "nginx/nginx.conf" ]; then
    echo "❌ nginx/nginx.conf not found. Please run this script from the project root."
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "📋 Current nginx configuration changes:"
echo "  ✅ client_max_body_size increased to 1G"
echo "  ✅ Timeout settings increased to 300s"
echo "  ✅ Proxy buffering disabled for large uploads"
echo ""

# Build the nginx image locally
echo "🔨 Building nginx image locally..."
docker build -t isr-datasets-nginx:latest ./nginx

if [ $? -eq 0 ]; then
    echo "✅ Nginx image built successfully"
else
    echo "❌ Failed to build nginx image"
    exit 1
fi

# Check if we should push to registry
read -p "🚀 Do you want to push the updated nginx image to GitHub Container Registry? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Tag for GitHub Container Registry
    echo "📦 Tagging image for GitHub Container Registry..."
    docker tag isr-datasets-nginx:latest ghcr.io/silvioheinze/isr-datasets-nginx:latest
    
    # Push to registry
    echo "⬆️  Pushing to GitHub Container Registry..."
    docker push ghcr.io/silvioheinze/isr-datasets-nginx:latest
    
    if [ $? -eq 0 ]; then
        echo "✅ Nginx image pushed successfully to GitHub Container Registry"
        echo ""
        echo "🎯 Next steps for production deployment:"
        echo "  1. Pull the updated image: docker pull ghcr.io/silvioheinze/isr-datasets-nginx:latest"
        echo "  2. Restart nginx service: docker compose -f docker-compose.prod.yml restart nginx"
        echo "  3. Or redeploy: docker compose -f docker-compose.prod.yml up -d nginx"
    else
        echo "❌ Failed to push nginx image to registry"
        exit 1
    fi
else
    echo "ℹ️  Skipping registry push. Image is available locally as 'isr-datasets-nginx:latest'"
    echo ""
    echo "🎯 To use locally:"
    echo "  1. Update docker-compose.yml to use local image"
    echo "  2. Restart: docker compose restart nginx"
fi

echo ""
echo "🎉 Nginx configuration update completed!"
echo ""
echo "📊 Upload limits now configured for:"
echo "  ✅ Maximum file size: 1GB"
echo "  ✅ Timeout: 5 minutes (300s)"
echo "  ✅ Optimized for large file uploads"
