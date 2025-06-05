#!/bin/bash

echo "🧪 Testing demo Demo Components"
echo "================================"

# Test 1: Database connectivity
echo "1️⃣  Testing TimescaleDB connection..."
db_test=$(docker-compose exec -T timescaledb psql -U postgres -d refinery_db -c "SELECT COUNT(*) FROM process_data;" 2>/dev/null)
if [[ $db_test == *"0"* ]] || [[ $db_test == *"1"* ]] || [[ $db_test == *"2"* ]]; then
    echo "   ✅ Database connected and accessible"
else
    echo "   ❌ Database connection failed"
    echo "   Debug: docker-compose exec timescaledb psql -U postgres -d refinery_db -c 'SELECT version();'"
fi

# Test 2: OPC-UA Server  
echo "2️⃣  Testing OPC-UA Server..."
if docker-compose logs opc-simulator 2>/dev/null | grep -q "Server started on port 4840"; then
    echo "   ✅ OPC-UA Server running on port 4840"
else
    echo "   ❌ OPC-UA Server not responding"
    echo "   Debug: docker-compose logs opc-simulator"
fi

# Test 3: Python Client
echo "3️⃣  Testing Python Client..."
if docker-compose logs python-client 2>/dev/null | grep -q "Demo Cycle"; then
    echo "   ✅ Python Client processing data"
else
    echo "   ❌ Python Client not working"
    echo "   Debug: docker-compose logs python-client"
fi

# Test 4: Grafana
echo "4️⃣  Testing Grafana..."
grafana_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/health 2>/dev/null)
if [ "$grafana_status" = "200" ]; then
    echo "   ✅ Grafana accessible on http://localhost:3000"
else
    echo "   ❌ Grafana not accessible (HTTP $grafana_status)"
    echo "   Debug: curl -v http://localhost:3000"
fi

# Test 5: Data Flow
echo "5️⃣  Testing Data Flow..."
sleep 5
recent_data=$(docker-compose exec -T timescaledb psql -U postgres -d refinery_db -c "SELECT COUNT(*) FROM process_data WHERE timestamp > NOW() - INTERVAL '2 minutes';" 2>/dev/null)
if [[ $recent_data == *"1"* ]] || [[ $recent_data == *"2"* ]] || [[ $recent_data == *"3"* ]]; then
    echo "   ✅ Fresh data being written to database"
else
    echo "   ❌ No recent data in database"
    echo "   Debug: Check python-client logs for errors"
fi

# Test 6: AI Decisions
echo "6️⃣  Testing AI Decision Engine..."
ai_decisions=$(docker-compose exec -T timescaledb psql -U postgres -d refinery_db -c "SELECT COUNT(*) FROM ai_decisions;" 2>/dev/null)
if [[ $ai_decisions == *"1"* ]] || [[ $ai_decisions == *"2"* ]] || [[ $ai_decisions == *"3"* ]]; then
    echo "   ✅ AI decisions being generated"
else
    echo "   ⚠️  No AI decisions yet (may need more time)"
fi

echo ""
echo "📊 Quick Data Summary:"
echo "====================="

# Show latest BIT-TQ value
latest_bittq=$(docker-compose exec -T timescaledb psql -U postgres -d refinery_db -c "SELECT bit_tq FROM process_data ORDER BY timestamp DESC LIMIT 1;" 2>/dev/null | grep -E "^\s*[0-9]" | xargs)
if [ ! -z "$latest_bittq" ]; then
    echo "🎯 Latest BIT-TQ: $latest_bittq dmm"
fi

# Show total AI decisions
total_decisions=$(docker-compose exec -T timescaledb psql -U postgres -d refinery_db -c "SELECT COUNT(*) FROM ai_decisions;" 2>/dev/null | grep -E "^\s*[0-9]" | xargs)
if [ ! -z "$total_decisions" ]; then
    echo "🤖 Total AI Decisions: $total_decisions"
fi

# Show data points
total_data=$(docker-compose exec -T timescaledb psql -U postgres -d refinery_db -c "SELECT COUNT(*) FROM process_data;" 2>/dev/null | grep -E "^\s*[0-9]" | xargs)
if [ ! -z "$total_data" ]; then
    echo "📈 Total Data Points: $total_data"
fi

echo ""
echo "🎬 Demo Status:"
echo "==============="

# Check if demo scenarios are running
if docker-compose logs opc-simulator 2>/dev/null | grep -q "Demo:"; then
    echo "✅ Demo scenarios are running automatically"
    echo "   Watch for: Problem → Human Fix → AI Optimization"
else
    echo "⚠️  Demo scenarios may not have started yet"
    echo "   Wait 1-2 minutes and check again"
fi

echo ""
echo "🔗 Quick Links:"
echo "==============="
echo "📊 Grafana Dashboard: http://localhost:3000 (admin/admin)"
echo "🗄️  Database Access: docker-compose exec timescaledb psql -U postgres -d refinery_db"
echo "📋 All Logs: docker-compose logs -f"
echo "🛑 Stop Demo: docker-compose down"

echo ""
echo "✅ Test completed!"