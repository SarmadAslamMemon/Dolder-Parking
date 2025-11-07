#!/bin/bash

# Docker Hub Deployment Script for Dolder Parking App
# Replace 'yourusername' with your actual Docker Hub username

DOCKER_USERNAME="sarmadaslam"
IMAGE_NAME="dolder-parking"
TAG="latest"

echo "🐳 Building Docker image for Dolder Parking..."
docker build -f Dockerfile.prod -t $DOCKER_USERNAME/$IMAGE_NAME:$TAG .

echo "📝 Tagging image..."
docker tag $DOCKER_USERNAME/$IMAGE_NAME:$TAG $DOCKER_USERNAME/$IMAGE_NAME:latest

echo "🔐 Logging into Docker Hub..."
docker login

echo "⬆️ Pushing to Docker Hub..."
docker push $DOCKER_USERNAME/$IMAGE_NAME:$TAG
docker push $DOCKER_USERNAME/$IMAGE_NAME:latest

echo "✅ Successfully deployed to Docker Hub!"
echo "📋 Your image is now available at: docker.io/$DOCKER_USERNAME/$IMAGE_NAME"
echo ""
echo "🚀 To run on any server:"
echo "docker run -d -p 8000:8000 $DOCKER_USERNAME/$IMAGE_NAME"
echo ""
echo "🌐 Or with docker-compose:"
echo "docker-compose -f docker-compose.prod.yml up -d"
