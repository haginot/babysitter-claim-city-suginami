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
echo "🌐 Access the application at:"
echo "   http://localhost:8081/frontend/babysitter-form.html"
echo "   or"
echo "   http://localhost:8081/"
echo ""
echo "📋 Available commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Stop: docker-compose down"
echo "  - Restart: docker-compose restart"
echo ""
echo "💡 データの編集方法:"
echo "   data/form_data.json ファイルを直接編集してください"
echo ""