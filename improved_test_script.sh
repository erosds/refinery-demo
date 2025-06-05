#!/bin/bash

echo "🧪 Testing Demo Demo Components (IMPROVED VERSION)"
echo "=================================================="

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test 1: Database connectivity
echo -e "${BLUE}1️⃣  Testing TimescaleDB connection...${NC}"
db_test=$(docker-compose exec -T timescaledb psql -U postgres -d refinery_db -c "SELECT COUNT(*) FROM process_data;" 2>/dev/null)
if [[ $db_test =~ [0-9]+ ]]; then
    echo -e "   ${GREEN}✅ Database connected and accessible${NC}"
    # Get actual count
    count=$(echo "$db_test" | grep -o '[0-9]\+' | head -1)
    echo -e "   ${BLUE}📊 Process data records: $count${NC}"
else
    echo -e "   ${RED}❌ Database connection failed${NC}"
    echo -e "   ${YELLOW}Debug: docker-compose exec timescaledb psql -U postgres -d refinery_db -c 'SELECT version();'${NC}"
fi

# Test 2: OPC-UA Server detailed check
echo -e "${BLUE}2️⃣  Testing OPC-UA Server...${NC}"
opc_status=$(docker-compose ps opc-simulator --format "table {{.Status}}" | tail -n +2)
if [[ $opc_status =~ "Up" ]]; then
    echo -e "   ${GREEN}✅ OPC-UA Container running${NC}"
    
    # Check if server is actually listening
    if docker-compose exec -T opc-simulator netstat -ln 2>/dev/null | grep -q ":4840"; then
        echo -e "   ${GREEN}✅ OPC-UA Server listening on port 4840${NC}"
    else
        echo -e "   ${YELLOW}⚠️  Port 4840 not ready yet${NC}"
    fi
    
    # Check logs for startup messages
    if docker-compose logs opc-simulator 2>/dev/null | grep -q "Server started\|Server initialized"; then
        echo -e "   ${GREEN}✅ OPC-UA Server properly initialized${NC}"
    else
        echo -e "   ${YELLOW}⚠️  Server may still be starting${NC}"
    fi
else
    echo -e "   ${RED}❌ OPC-UA Container not running${NC}"
    echo -e "   ${YELLOW}Debug: docker-compose logs opc-simulator${NC}"
fi

# Test 3: Python Client detailed analysis
echo -e "${BLUE}3️⃣  Testing Python Client...${NC}"
client_logs=$(docker-compose logs python-client --tail=20 2>/dev/null)

if echo "$client_logs" | grep -q "Demo Cycle"; then
    echo -e "   ${GREEN}✅ Python Client is running cycles${NC}"
    
    # Check if it's reading real OPC data
    if echo "$client_logs" | grep -q "Current BIT-TQ: 0.0"; then
        echo -e "   ${YELLOW}⚠️  Client reading BIT-TQ as 0.0 (OPC connection issue)${NC}"
        echo -e "   ${YELLOW}💡 Checking OPC connection details...${NC}"
        
        if echo "$client_logs" | grep -q "OPC-UA connected successfully"; then
            echo -e "   ${GREEN}✅ OPC connection successful${NC}"
        else
            echo -e "   ${RED}❌ OPC connection failing${NC}"
        fi
    else
        echo -e "   ${GREEN}✅ Client reading valid BIT-TQ values${NC}"
    fi
    
    # Check if AI decisions are being made
    if echo "$client_logs" | grep -q "AI Decision"; then
        echo -e "   ${GREEN}✅ AI decisions being generated${NC}"
    else
        echo -e "   ${YELLOW}⚠️  No AI decisions in recent logs${NC}"
    fi
    
else
    echo -e "   ${RED}❌ Python Client not working properly${NC}"
    echo -e "   ${YELLOW}Debug: docker-compose logs python-client --tail=50${NC}"
fi

# Test 4: Grafana with dashboard check
echo -e "${BLUE}4️⃣  Testing Grafana...${NC}"
grafana_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/health 2>/dev/null)
if [ "$grafana_status" = "200" ]; then
    echo -e "   ${GREEN}✅ Grafana accessible on http://localhost:3000${NC}"
    
    # Check for dashboard errors
    dashboard_errors=$(docker-compose logs grafana 2>/dev/null | grep -i "dashboard.*error" | tail -1)
    if [ ! -z "$dashboard_errors" ]; then
        echo -e "   ${YELLOW}⚠️  Dashboard loading issues detected${NC}"
        echo -e "   ${YELLOW}📝 Last error: $dashboard_errors${NC}"
    else
        echo -e "   ${GREEN}✅ No dashboard errors detected${NC}"
    fi
else
    echo -e "   ${RED}❌ Grafana not accessible (HTTP $grafana_status)${NC}"
    echo -e "   ${YELLOW}Debug: curl -v http://localhost:3000${NC}"
fi

# Test 5: Data Flow with actual values
echo -e "${BLUE}5️⃣  Testing Data Flow...${NC}"
sleep 5
recent_data=$(docker-compose exec -T timescaledb psql -U postgres -d refinery_db -c "SELECT COUNT(*), AVG(bit_tq), MAX(timestamp) FROM process_data WHERE timestamp > NOW() - INTERVAL '2 minutes';" 2>/dev/null)

if [[ $recent_data =~ [0-9]+ ]]; then
    count=$(echo "$recent_data" | grep -o '[0-9]\+' | head -1)
    if [ "$count" -gt 0 ]; then
        echo -e "   ${GREEN}✅ Fresh data being written to database${NC}"
        echo -e "   ${BLUE}📊 Recent records: $count${NC}"
        
        # Extract BIT-TQ average if available
        avg_bittq=$(echo "$recent_data" | grep -o '[0-9]\+\.[0-9]\+' | head -1)
        if [ ! -z "$avg_bittq" ]; then
            echo -e "   ${BLUE}🎯 Average BIT-TQ: $avg_bittq${NC}"
        fi
    else
        echo -e "   ${RED}❌ No recent data in database${NC}"
        echo -e "   ${YELLOW}Debug: Check python-client logs for errors${NC}"
    fi
else
    echo -e "   ${RED}❌ Database query failed${NC}"
fi

# Test 6: AI Decisions with details
echo -e "${BLUE}6️⃣  Testing AI Decision Engine...${NC}"
ai_data=$(docker-compose exec -T timescaledb psql -U postgres -d refinery_db -c "SELECT COUNT(*), COALESCE(SUM(savings_eur_hour), 0) as total_savings FROM ai_decisions;" 2>/dev/null)

if [[ $ai_data =~ [0-9]+ ]]; then
    ai_count=$(echo "$ai_data" | grep -o '[0-9]\+' | head -1)
    if [ "$ai_count" -gt 0 ]; then
        echo -e "   ${GREEN}✅ AI decisions being generated${NC}"
        echo -e "   ${BLUE}🤖 Total decisions: $ai_count${NC}"
        
        # Extract savings if available
        savings=$(echo "$ai_data" | grep -o '[0-9]\+\.[0-9]\+' | tail -1)
        if [ ! -z "$savings" ]; then
            echo -e "   ${BLUE}💰 Total savings: €$savings/hour${NC}"
        fi
    else
        echo -e "   ${YELLOW}⚠️  No AI decisions yet (may need more time)${NC}"
    fi
else
    echo -e "   ${RED}❌ AI decisions query failed${NC}"
fi

# Test 7: Container Health Check
echo -e "${BLUE}7️⃣  Container Health Status...${NC}"
containers=("demo-timescaledb" "demo-opc-simulator" "demo-python-client" "demo-grafana")

for container in "${containers[@]}"; do
    status=$(docker ps --format "table {{.Names}}\t{{.Status}}" | grep "$container" | awk '{print $2}')
    if [[ $status =~ "Up" ]]; then
        echo -e "   ${GREEN}✅ $container: Running${NC}"
        
        # Check memory usage
        memory=$(docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}" | grep "$container" | awk '{print $2}' 2>/dev/null)
        if [ ! -z "$memory" ]; then
            echo -e "   ${BLUE}📊 Memory: $memory${NC}"
        fi
    else
        echo -e "   ${RED}❌ $container: Not running${NC}"
    fi
done

echo ""
echo -e "${BLUE}📊 Quick Data Summary:${NC}"
echo "====================="

# Show latest BIT-TQ value with timestamp
latest_data=$(docker-compose exec -T timescaledb psql -U postgres -d refinery_db -c "SELECT bit_tq, timestamp FROM process_data ORDER BY timestamp DESC LIMIT 1;" 2>/dev/null)
if [[ $latest_data =~ [0-9] ]]; then
    latest_bittq=$(echo "$latest_data" | grep -o '[0-9]\+\.[0-9]\+' | head -1)
    if [ ! -z "$latest_bittq" ]; then
        echo -e "${GREEN}🎯 Latest BIT-TQ: $latest_bittq dmm${NC}"
    fi
fi

# Show total AI decisions with recent activity
total_decisions=$(docker-compose exec -T timescaledb psql -U postgres -d refinery_db -c "SELECT COUNT(*) FROM ai_decisions;" 2>/dev/null | grep -E "^\s*[0-9]" | xargs)
recent_decisions=$(docker-compose exec -T timescaledb psql -U postgres -d refinery_db -c "SELECT COUNT(*) FROM ai_decisions WHERE timestamp > NOW() - INTERVAL '10 minutes';" 2>/dev/null | grep -E "^\s*[0-9]" | xargs)

if [ ! -z "$total_decisions" ]; then
    echo -e "${GREEN}🤖 Total AI Decisions: $total_decisions${NC}"
    if [ ! -z "$recent_decisions" ] && [ "$recent_decisions" -gt 0 ]; then
        echo -e "${GREEN}🤖 Recent AI Decisions (10min): $recent_decisions${NC}"
    fi
fi

# Show data points with rate
total_data=$(docker-compose exec -T timescaledb psql -U postgres -d refinery_db -c "SELECT COUNT(*) FROM process_data;" 2>/dev/null | grep -E "^\s*[0-9]" | xargs)
recent_data_count=$(docker-compose exec -T timescaledb psql -U postgres -d refinery_db -c "SELECT COUNT(*) FROM process_data WHERE timestamp > NOW() - INTERVAL '5 minutes';" 2>/dev/null | grep -E "^\s*[0-9]" | xargs)

if [ ! -z "$total_data" ]; then
    echo -e "${GREEN}📈 Total Data Points: $total_data${NC}"
    if [ ! -z "$recent_data_count" ] && [ "$recent_data_count" -gt 0 ]; then
        rate=$(( recent_data_count / 5 ))
        echo -e "${GREEN}📈 Data Rate: ~$rate points/minute${NC}"
    fi
fi

echo ""
echo -e "${BLUE}🎬 Demo Status:${NC}"
echo "==============="

# Check demo scenarios with specific patterns
opc_logs=$(docker-compose logs opc-simulator --tail=50 2>/dev/null)
if echo "$opc_logs" | grep -q "Demo:"; then
    echo -e "${GREEN}✅ Demo scenarios are running automatically${NC}"
    
    # Check for specific demo phases
    if echo "$opc_logs" | grep -q "Creating BIT-TQ problem"; then
        echo -e "${YELLOW}🎬 Phase: Problem Creation${NC}"
    elif echo "$opc_logs" | grep -q "Human operator adjusts"; then
        echo -e "${YELLOW}🎬 Phase: Human Intervention${NC}"
    elif echo "$opc_logs" | grep -q "AI takes control"; then
        echo -e "${GREEN}🎬 Phase: AI Optimization${NC}"
    elif echo "$opc_logs" | grep -q "Anomaly detected"; then
        echo -e "${RED}🎬 Phase: Anomaly Detection${NC}"
    else
        echo -e "${BLUE}🎬 Phase: Baseline Operation${NC}"
    fi
    
    echo -e "${BLUE}   Watch for: Problem → Human Fix → AI Optimization → Results${NC}"
else
    echo -e "${YELLOW}⚠️  Demo scenarios may not have started yet${NC}"
    echo -e "${BLUE}   Wait 1-2 minutes and check again${NC}"
fi

# Performance summary
echo ""
echo -e "${BLUE}⚡ Performance Check:${NC}"
echo "==================="

# Check if system is performing well
cpu_usage=$(docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}" 2>/dev/null | grep -E "demo-" | awk '{print $2}' | sed 's/%//' | sort -nr | head -1)
if [ ! -z "$cpu_usage" ]; then
    if (( $(echo "$cpu_usage > 80" | bc -l) )); then
        echo -e "${RED}⚠️  High CPU usage detected: $cpu_usage%${NC}"
    else
        echo -e "${GREEN}✅ CPU usage normal: $cpu_usage%${NC}"
    fi
fi

echo ""
echo -e "${BLUE}🔗 Quick Links:${NC}"
echo "==============="
echo -e "${GREEN}📊 Grafana Dashboard: http://localhost:3000 (admin/admin)${NC}"
echo -e "${BLUE}🗄️  Database Access: docker-compose exec timescaledb psql -U postgres -d refinery_db${NC}"
echo -e "${BLUE}📋 All Logs: docker-compose logs -f${NC}"
echo -e "${BLUE}🛑 Stop Demo: docker-compose down${NC}"

echo ""
echo -e "${GREEN}✅ Test completed!${NC}"

# Final recommendations
echo ""
echo -e "${BLUE}💡 Troubleshooting Tips:${NC}"
echo "======================="
if echo "$client_logs" | grep -q "Current BIT-TQ: 0.0"; then
    echo -e "${YELLOW}• OPC connection issue detected - try restarting python-client:${NC}"
    echo -e "  ${BLUE}docker-compose restart python-client${NC}"
fi

if [ ! -z "$dashboard_errors" ]; then
    echo -e "${YELLOW}• Grafana dashboard errors detected - check dashboard JSON format${NC}"
fi

if [ "$recent_data_count" -eq 0 ]; then
    echo -e "${YELLOW}• No recent data flow - check all services are communicating${NC}"
fi