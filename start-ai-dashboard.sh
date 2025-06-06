#!/bin/bash

echo "🚀 Starting AI Control Dashboard Demo"
echo "======================================"

# Verifica che il sistema sia attivo
echo "🔍 Checking system status..."

# Verifica servizi Docker
if ! docker ps | grep -q "demo-"; then
    echo "❌ Demo services not running. Starting them first..."
    ./start-demo-enhanced.sh
    echo "⏳ Waiting for services to fully initialize..."
    sleep 30
fi

# Verifica API server
echo "🔌 Testing API server..."
if curl -s http://localhost:5000/api/status > /dev/null; then
    echo "✅ API server is responding"
else
    echo "❌ API server not responding. Check if it's running:"
    echo "   docker-compose logs api-server"
    exit 1
fi

# Verifica Grafana
echo "📊 Testing Grafana..."
if curl -s http://localhost:3000/api/health > /dev/null; then
    echo "✅ Grafana is responding"
else
    echo "❌ Grafana not responding. Check if it's running:"
    echo "   docker-compose logs grafana"
    exit 1
fi

echo ""
echo "🎉 All systems ready!"
echo ""
echo "📱 AI Control Dashboard Options:"
echo ""
echo "1. 🌐 HTML Dashboard (Recommended):"
echo "   Open: ai-control-dashboard.html in your browser"
echo "   Features: Full AI control with buttons"
echo ""
echo "2. 📊 Direct Grafana:"
echo "   URL: http://localhost:3000/d/dashboard-demo-refinery-enhanced"
echo "   Login: admin/admin"
echo ""
echo "3. 🔧 Manual API Testing:"
echo "   Check status: curl http://localhost:5000/api/status"
echo "   Get decision: curl http://localhost:5000/api/ai-decisions/latest"
echo "   Apply AI:     curl -X POST http://localhost:5000/api/ai-decisions/apply"
echo ""
echo "🎬 Demo Workflow:"
echo "================"
echo "1. Open ai-control-dashboard.html"
echo "2. Click 'Aggiorna Stato' to check current BIT-TQ"
echo "3. Click 'Visualizza Ultima Decisione' to see AI recommendations"
echo "4. Click 'Applica Decisione AI' to implement optimization"
echo "5. Watch BIT-TQ improve in real-time on the dashboard"
echo "6. Use 'Reset Controllo Umano' to return to baseline"
echo ""

# Se possibile, apri il browser
if [ -f "ai-control-dashboard.html" ]; then
    echo "🌐 Opening AI Control Dashboard..."
    
    if command -v open &> /dev/null; then
        open ai-control-dashboard.html
    elif command -v xdg-open &> /dev/null; then
        xdg-open ai-control-dashboard.html
    else
        echo "   Please open ai-control-dashboard.html manually in your browser"
    fi
else
    echo "⚠️  ai-control-dashboard.html not found in current directory"
    echo "   Please create it using the provided HTML code"
fi

echo ""
echo "✅ Demo ready! Enjoy testing the AI optimization!"