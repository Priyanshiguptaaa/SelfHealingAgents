#!/bin/bash

echo "🚀 Starting Self-Healing E-commerce Agents System (Simple Mode)"
echo "==============================================================="
echo ""
echo "This setup uses SQLite and in-memory event bus (no Docker required)"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+ first."
    exit 1
fi

echo "✅ Prerequisites check passed"
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
echo "💡 This simplified version uses:"
echo "• SQLite database (no PostgreSQL needed)"
echo "• In-memory event bus (no Redis needed)"
echo "• No Docker containers required"
echo ""
echo "Ready to start! Run the commands above in separate terminals." 