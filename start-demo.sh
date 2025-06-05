#!/bin/bash

echo "🏭 Starting demo - Digital Twin & AI Analytics"
echo "=================================================="

# Verifica prerequisiti
echo "🔍 Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

# Verifica porte disponibili
echo "🔌 Checking required ports..."
for port in 3000 4840 5432; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo "❌ Port $port is already in use. Please free it first."
        exit 1
    fi
done

echo "✅ All prerequisites met!"

# Pulisci installazione precedente se esiste
echo "🧹 Cleaning previous installation..."
docker-compose down -v 2>/dev/null || true

# Avvia servizi
echo "🚀 Starting demo Demo services..."
docker-compose up -d

# Attendi inizializzazione
echo "⏳ Waiting for services to initialize..."
echo "   - TimescaleDB: Starting..."
sleep 10

echo "   - OPC-UA Simulator: Starting..." 
sleep 5

echo "   - Python Client: Starting..."
sleep 10

echo "   - Grafana: Starting..."
sleep 5

# Verifica stato servizi
echo "🔍 Checking service health..."

services=("demo-timescaledb" "demo-opc-simulator" "demo-python-client" "demo-grafana")
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
    echo "🎉 demo Demo is ready!"
    echo ""
    echo "📊 Open Grafana Dashboard:"
    echo "   URL: http://localhost:3000"
    echo "   Login: admin / admin"
    echo ""
    echo "🎬 Demo Scenario (automatic 5-minute cycle):"
    echo "   1. Baseline data (BIT-TQ ~45)"
    echo "   2. Problem detection"  
    echo "   3. Human intervention (partial fix)"
    echo "   4. AI optimization (complete solution)"
    echo "   5. Results: BIT-TQ target + energy savings"
    echo ""
    echo "🔍 Monitor logs (optional):"
    echo "   docker-compose logs -f"
    echo ""
    echo "🛑 Stop demo:"
    echo "   docker-compose down"
    echo ""
    
    # Apri browser automaticamente se possibile
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
    echo "   ./start-demo.sh"
fi