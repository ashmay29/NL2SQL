#!/bin/bash

echo "========================================="
echo "NL2SQL System - Quick Start"
echo "========================================="
echo ""

# Check if .env exists
if [ ! -f "backend/.env" ]; then
    echo "⚠️  Creating .env file from template..."
    cp backend/.env.example backend/.env
    echo "✅ Created backend/.env - Please edit with your credentials"
    echo ""
fi

# Start Docker services
echo "🚀 Starting Docker services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check health
echo ""
echo "🏥 Checking health..."
curl -s http://localhost:8000/health | python -m json.tool || echo "Backend not ready yet"

echo ""
echo "========================================="
echo "✅ Services Started!"
echo "========================================="
echo ""
echo "📍 Access points:"
echo "   - Backend API:  http://localhost:8000"
echo "   - API Docs:     http://localhost:8000/docs"
echo "   - Frontend:     http://localhost:3000"
echo "   - Qdrant:       http://localhost:6333/dashboard"
echo ""
echo "📝 Logs:"
echo "   docker-compose logs -f backend"
echo "   docker-compose logs -f frontend"
echo ""
echo "🛑 Stop:"
echo "   docker-compose down"
echo ""
