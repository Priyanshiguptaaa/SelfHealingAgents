#!/bin/bash

echo "🚀 Starting Self-Healing E-commerce Agents System"
echo "=================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Start services
echo "📦 Starting Redis and PostgreSQL services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "✅ Services are running"
else
    echo "❌ Failed to start services"
    exit 1
fi

echo ""
echo "🔧 Setup Instructions:"
echo "======================"
echo ""
echo "1. Backend Setup:"
echo "   cd backend"
echo "   pip install -r requirements.txt"
echo "   python main.py"
echo ""
echo "2. Frontend Setup (in another terminal):"
echo "   cd frontend"
echo "   npm install"
echo "   npm run dev"
echo ""
echo "3. Open your browser:"
echo "   Frontend: http://localhost:5173"
echo "   Backend API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "4. Trigger a healing demo:"
echo "   Click 'Trigger Failure' button in the UI"
echo "   Or use: curl -X POST http://localhost:8000/api/trigger-failure"
echo ""
echo "🎯 The system will demonstrate:"
echo "• Real-time failure detection"
echo "• Autonomous root cause analysis"
echo "• Code patch generation using Morph API"
echo "• Safe patch application with rollback"
echo "• Verification and healing completion"
echo "• Live UI updates via Server-Sent Events"
echo ""
echo "💡 To stop services: docker-compose down" 