#!/bin/bash

echo "🚀 Starting Babysitter Form Application..."
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

# Build and start the container
echo "📦 Building Docker image..."
docker-compose build

echo ""
echo "🏃 Starting container..."
docker-compose up -d

echo ""
echo "✅ Application is running!"
echo ""
echo "🌐 Access the application at: http://localhost:8080/babysitter-form-with-print.html"
echo ""
echo "📋 Available commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Stop: docker-compose down"
echo "  - Restart: docker-compose restart"
echo ""