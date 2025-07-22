#!/bin/bash

# ToggleBank RAG with Anti-Hallucination System - Docker Runner
# This script makes it easy to run the application with Docker

set -e

echo "🚀 ToggleBank RAG with Anti-Hallucination System"
echo "================================================"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with your configuration:"
    echo ""
    echo "LAUNCHDARKLY_SDK_KEY=sdk-your-key-here"
    echo "LAUNCHDARKLY_AI_CONFIG_KEY=your-ai-config-key"
    echo "LAUNCHDARKLY_LLM_JUDGE_KEY=llm-as-judge"
    echo "AWS_REGION=us-east-1"
    echo "AWS_ACCESS_KEY_ID=your-aws-access-key"
    echo "AWS_SECRET_ACCESS_KEY=your-aws-secret-key"
    echo ""
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running!"
    echo "Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: docker-compose is not installed!"
    echo "Please install docker-compose and try again."
    exit 1
fi

echo "✅ Environment check passed"
echo "🔧 Building and starting the application..."

# Build and run with docker-compose
docker-compose up --build

echo "👋 Application stopped" 