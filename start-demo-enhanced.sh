#!/bin/bash

echo "🚀 Starting Enhanced Demo - Digital Twin & AI Analytics with Control"
echo "================================================================="

# Check prerequisites
echo "🔍 Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

# Check required ports
echo "🔌 Checking required ports..."
for port in 3000 4840 5000 5432; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "❌ Port $port is already in use. Please free it first."
        exit 1
    fi
done

echo "✅ All prerequisites met!"

# Clean previous installation
echo "🧹 Cleaning previous installation..."
docker-compose down -v 2>/dev/null || true

# Start services
echo "🚀 Starting Enhanced Demo services..."
docker-compose up -d

# Wait for initialization
echo "⏳ Waiting for services to initialize..."
echo "   - TimescaleDB: Starting..."
sleep 15

echo "   - OPC-UA Simulator: Starting..." 
sleep 10

echo "   - Python Client: Starting..."
sleep 10

echo "   - API Server: Starting..."
sleep 5

echo "   - Grafana: Starting..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

services=("demo-timescaledb" "demo-opc-simulator" "demo-python-client" "demo-grafana" "demo-api-server")
all_healthy=true

for service in "${services[@]}"; do
    if docker ps --filter "name=$service" --filter "status=running" --quiet | grep -q .; then
        echo "   ✅ $service: Running"
    else
        echo "   ❌ $service: Not running"
        all_healthy=false
    fi
done

if [ "$all_healthy" = true ]; then
    echo ""
    echo "🎉 Enhanced Demo is ready!"
    echo ""
    echo "📊 Open Enhanced Grafana Dashboard:"
    echo "   URL: http://localhost:3000"
    echo "   Login: admin / admin"
    echo ""
    echo "🤖 AI Control Features:"
    echo "   • View AI optimization recommendations"
    echo "   • Apply AI decisions with one click"
    echo "   • Reset to human control mode"
    echo "   • Real-time performance monitoring"
    echo ""
    echo "🔧 API Endpoints (for testing):"
    echo "   • http://localhost:5000/api/status"
    echo "   • http://localhost:5000/api/ai-decisions/latest"
    echo ""
    echo "🎬 Enhanced Demo Scenario:"
    echo "   1. Baseline data (BIT-TQ ~45)"
    echo "   2. AI generates optimization recommendations"  
    echo "   3. Click 'Apply AI Decision' button"
    echo "   4. Watch BIT-TQ improve to target (50+)"
    echo "   5. See energy savings and CO2 reduction"
    echo ""
    echo "🔍 Monitor logs (optional):"
    echo "   docker-compose logs -f"
    echo ""
    echo "🛑 Stop demo:"
    echo "   docker-compose down"
    echo ""
    
    # Open browser automatically if possible
    if command -v open &> /dev/null; then
        echo "🌐 Opening browser..."
        open http://localhost:3000
    elif command -v xdg-open &> /dev/null; then
        echo "🌐 Opening browser..."
        xdg-open http://localhost:3000
    fi
    
else
    echo ""
    echo "❌ Some services failed to start. Check logs:"
    echo "   docker-compose logs"
    echo ""
    echo "🔧 Try restarting:"
    echo "   docker-compose down"
    echo "   ./start-demo-enhanced.sh"
fi
