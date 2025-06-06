#!/bin/bash

echo "🚀 Setting up Enhanced Demo with AI Control"
echo "================================================"

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p api-server
mkdir -p grafana-config/provisioning/dashboards

# Create API server files
echo "📝 Creating API server files..."

cat > api-server/app.py << 'EOF'
"""
API Server per applicare decisioni AI al server OPC-UA
Espone endpoint REST per la dashboard Grafana
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import asyncio
import psycopg2
from asyncua import Client
import json
import os
import logging
from datetime import datetime
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class AIDecisionApplier:
    def __init__(self):
        self.opc_url = f"opc.tcp://{os.getenv('OPC_HOST', 'localhost')}:4840/refinery"
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'refinery_db'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'password'),
            'port': 5432
        }
        
    def get_latest_ai_decision(self) -> Optional[Dict]:
        """Recupera l'ultima decisione AI non ancora applicata"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    parameters_changed, 
                    predicted_bit_tq,
                    predicted_energy_saving,
                    predicted_co2_reduction,
                    confidence,
                    timestamp
                FROM ai_decisions 
                WHERE decision_applied = false 
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            if result:
                return {
                    'parameters_changed': json.loads(result[0]) if result[0] else {},
                    'predicted_bit_tq': result[1],
                    'predicted_energy_saving': result[2],
                    'predicted_co2_reduction': result[3],
                    'confidence': result[4],
                    'timestamp': result[5]
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest AI decision: {e}")
            return None
        finally:
            conn.close()
    
    async def apply_ai_parameters(self, parameters: Dict) -> bool:
        """Applica i parametri AI al server OPC-UA"""
        try:
            client = Client(self.opc_url)
            client.set_session_timeout(10000)
            client.set_security_string("None")
            
            await client.connect()
            logger.info("🔗 Connected to OPC-UA server for parameter application")
            
            # Trova il nodo della raffineria
            root = client.get_root_node()
            objects = await root.get_child(["0:Objects"])
            children = await objects.get_children()
            
            refinery_node = None
            for child in children:
                display_name = await child.read_display_name()
                if "Refinery" in str(display_name):
                    refinery_node = child
                    break
            
            if not refinery_node:
                logger.error("❌ Refinery node not found")
                return False
            
            # Applica i parametri
            variables = await refinery_node.get_children()
            applied_count = 0
            
            for var in variables:
                browse_name = await var.read_browse_name()
                var_name = str(browse_name.Name)
                
                if var_name in parameters:
                    try:
                        new_value = parameters[var_name]
                        await var.write_value(float(new_value))
                        logger.info(f"✅ Applied {var_name}: {new_value}")
                        applied_count += 1
                    except Exception as e:
                        logger.error(f"❌ Failed to apply {var_name}: {e}")
            
            # Imposta modalità AI attiva
            for var in variables:
                browse_name = await var.read_browse_name()
                var_name = str(browse_name.Name)
                if var_name == 'operator_mode':
                    await var.write_value(1.0)  # AI control
                    logger.info("🤖 AI control mode activated")
                    break
            
            await client.disconnect()
            logger.info(f"✅ Successfully applied {applied_count} parameters")
            return applied_count > 0
            
        except Exception as e:
            logger.error(f"❌ Error applying AI parameters: {e}")
            return False
    
    def mark_decision_as_applied(self):
        """Marca l'ultima decisione come applicata"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE ai_decisions 
                SET decision_applied = true, operator_approved = true
                WHERE id = (
                    SELECT id FROM ai_decisions 
                    WHERE decision_applied = false 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                )
            """)
            
            conn.commit()
            logger.info("✅ Decision marked as applied")
            
        except Exception as e:
            logger.error(f"Error marking decision as applied: {e}")
        finally:
            conn.close()

# Inizializza l'applier
applier = AIDecisionApplier()

@app.route('/api/ai-decisions/latest', methods=['GET'])
def get_latest_decision():
    """Endpoint per ottenere l'ultima decisione AI"""
    decision = applier.get_latest_ai_decision()
    if decision:
        return jsonify({
            'success': True,
            'decision': decision
        })
    else:
        return jsonify({
            'success': False,
            'message': 'No pending AI decisions found'
        })

@app.route('/api/ai-decisions/apply', methods=['POST'])
def apply_ai_decision():
    """Endpoint per applicare l'ultima decisione AI"""
    try:
        # Recupera l'ultima decisione
        decision = applier.get_latest_ai_decision()
        if not decision:
            return jsonify({
                'success': False,
                'message': 'No pending AI decisions to apply'
            })
        
        # Applica i parametri
        success = asyncio.run(applier.apply_ai_parameters(decision['parameters_changed']))
        
        if success:
            # Marca come applicata
            applier.mark_decision_as_applied()
            
            return jsonify({
                'success': True,
                'message': 'AI decision applied successfully',
                'applied_parameters': decision['parameters_changed'],
                'predicted_bit_tq': decision['predicted_bit_tq'],
                'confidence': decision['confidence']
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to apply AI decision to OPC-UA server'
            })
            
    except Exception as e:
        logger.error(f"Error in apply_ai_decision: {e}")
        return jsonify({
            'success': False,
            'message': f'Error applying decision: {str(e)}'
        })

@app.route('/api/process/reset', methods=['POST'])
def reset_to_human_control():
    """Endpoint per resettare il controllo umano"""
    try:
        # Reset parameters to baseline
        baseline_params = {
            'fc1065': 127.3,
            'li40054': 68.2,
            'fc31007': 89.1,
            'pi18213': 2.14,
            'operator_mode': 0.0  # Human control
        }
        
        success = asyncio.run(applier.apply_ai_parameters(baseline_params))
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Process reset to human control'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to reset process'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error resetting process: {str(e)}'
        })

@app.route('/api/status', methods=['GET'])
def get_status():
    """Endpoint per lo status dell'API"""
    return jsonify({
        'success': True,
        'message': 'AI Decision API is running',
        'endpoints': [
            '/api/ai-decisions/latest',
            '/api/ai-decisions/apply',
            '/api/process/reset',
            '/api/status'
        ]
    })

if __name__ == '__main__':
    logger.info("🚀 Starting AI Decision API Server...")
    app.run(host='0.0.0.0', port=5000, debug=False)
EOF

cat > api-server/requirements.txt << 'EOF'
flask==2.3.3
flask-cors==4.0.0
asyncua==1.0.6
psycopg2-binary==2.9.9
EOF

cat > api-server/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
EOF

# Update the dashboard with the enhanced version
echo "📊 Creating enhanced dashboard..."

cat > grafana-config/provisioning/dashboards/dart-demo-enhanced.json << 'EOF'
{
  "annotations": {
    "list": [
      {
        "builtIn": 1,
        "datasource": {
          "type": "grafana",
          "uid": "-- Grafana --"
        },
        "enable": true,
        "hide": true,
        "iconColor": "rgba(0, 211, 255, 1)",
        "name": "Annotations & Alerts",
        "type": "dashboard"
      }
    ]
  },
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 0,
  "id": null,
  "links": [],
  "panels": [
    {
      "datasource": {
        "type": "grafana-postgresql-datasource",
        "uid": "P40AE60E18F02DE32"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "custom": {
            "axisBorderShow": false,
            "axisCenteredZero": false,
            "axisColorMode": "text",
            "axisLabel": "",
            "axisPlacement": "auto",
            "barAlignment": 0,
            "barWidthFactor": 0.6,
            "drawStyle": "line",
            "fillOpacity": 10,
            "gradientMode": "none",
            "hideFrom": {
              "legend": false,
              "tooltip": false,
              "viz": false
            },
            "insertNulls": false,
            "lineInterpolation": "linear",
            "lineWidth": 2,
            "pointSize": 5,
            "scaleDistribution": {
              "type": "linear"
            },
            "showPoints": "auto",
            "spanNulls": false,
            "stacking": {
              "group": "A",
              "mode": "none"
            },
            "thresholdsStyle": {
              "mode": "line"
            }
          },
          "mappings": [],
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {
                "color": "green",
                "value": null
              },
              {
                "color": "red",
                "value": 40
              },
              {
                "color": "yellow",
                "value": 45
              },
              {
                "color": "green",
                "value": 50
              }
            ]
          },
          "unit": "dmm",
          "min": 35,
          "max": 65
        },
        "overrides": [
          {
            "matcher": {
              "id": "byName",
              "options": "Target"
            },
            "properties": [
              {
                "id": "color",
                "value": {
                  "fixedColor": "red",
                  "mode": "fixed"
                }
              },
              {
                "id": "custom.lineStyle",
                "value": {
                  "dash": [10, 10],
                  "fill": "dash"
                }
              },
              {
                "id": "custom.lineWidth",
                "value": 3
              }
            ]
          }
        ]
      },
      "gridPos": {
        "h": 8,
        "w": 16,
        "x": 0,
        "y": 0
      },
      "id": 1,
      "options": {
        "legend": {
          "calcs": ["lastNotNull"],
          "displayMode": "list",
          "placement": "bottom",
          "showLegend": true
        },
        "tooltip": {
          "hideZeros": false,
          "mode": "multi",
          "sort": "none"
        }
      },
      "targets": [
        {
          "datasource": {
            "type": "grafana-postgresql-datasource",
            "uid": "P40AE60E18F02DE32"
          },
          "editorMode": "code",
          "format": "time_series",
          "rawQuery": true,
          "rawSql": "SELECT \\n    p.timestamp as time,\\n    p.bit_tq as \\\"BIT-TQ Attuale\\\",\\n    50 as \\\"Target\\\",\\n    CASE \\n        WHEN p.data_source = 'ai_control' THEN p.bit_tq\\n        ELSE NULL\\n    END as \\\"AI Control\\\"\\nFROM process_data p\\nWHERE $__timeFilter(p.timestamp) \\nORDER BY p.timestamp ASC",
          "refId": "A"
        }
      ],
      "title": "🎯 BIT-TQ Penetrazione Bitume (Target: 50 dmm)",
      "type": "timeseries"
    },
    {
      "datasource": {
        "type": "-"
      },
      "gridPos": {
        "h": 8,
        "w": 8,
        "x": 16,
        "y": 0
      },
      "id": 9,
      "options": {
        "content": "<div style=\\\"background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; text-align: center; height: 100%; display: flex; flex-direction: column; justify-content: space-around;\\\">\\n\\n<h2 style=\\\"color: white; margin: 0;\\\">🤖 AI Control Panel</h2>\\n\\n<div style=\\\"background: rgba(255,255,255,0.1); padding: 15px; border-radius: 8px; margin: 10px 0;\\\">\\n<h3 style=\\\"color: white; margin: 0 0 10px 0;\\\">Latest AI Decision</h3>\\n<div id=\\\"ai-decision-info\\\" style=\\\"color: #f0f0f0; font-size: 14px;\\\">\\nLoading...\\n</div>\\n</div>\\n\\n<div style=\\\"display: flex; gap: 10px; justify-content: center;\\\">\\n<button id=\\\"apply-ai-btn\\\" onclick=\\\"applyAIDecision()\\\" style=\\\"\\n    background: linear-gradient(45deg, #4CAF50, #45a049);\\n    color: white;\\n    border: none;\\n    padding: 12px 20px;\\n    border-radius: 25px;\\n    cursor: pointer;\\n    font-weight: bold;\\n    box-shadow: 0 4px 8px rgba(0,0,0,0.2);\\n    transition: all 0.3s ease;\\n    flex: 1;\\n\\\" onmouseover=\\\"this.style.transform='scale(1.05)'\\\" onmouseout=\\\"this.style.transform='scale(1)'\\\">\\n✨ Apply AI Decision\\n</button>\\n\\n<button id=\\\"reset-btn\\\" onclick=\\\"resetToHuman()\\\" style=\\\"\\n    background: linear-gradient(45deg, #ff6b6b, #ff5252);\\n    color: white;\\n    border: none;\\n    padding: 12px 20px;\\n    border-radius: 25px;\\n    cursor: pointer;\\n    font-weight: bold;\\n    box-shadow: 0 4px 8px rgba(0,0,0,0.2);\\n    transition: all 0.3s ease;\\n    flex: 1;\\n\\\" onmouseover=\\\"this.style.transform='scale(1.05)'\\\" onmouseout=\\\"this.style.transform='scale(1)'\\\">\\n🔄 Reset to Human\\n</button>\\n</div>\\n\\n<div id=\\\"status-message\\\" style=\\\"color: #f0f0f0; margin-top: 15px; font-size: 12px; min-height: 20px;\\\">\\nReady for AI optimization\\n</div>\\n\\n</div>\\n\\n<script>\\nlet apiBaseUrl = 'http://localhost:5000/api';\\n\\nasync function loadLatestDecision() {\\n    try {\\n        const response = await fetch(`${apiBaseUrl}/ai-decisions/latest`);\\n        const data = await response.json();\\n        \\n        const infoDiv = document.getElementById('ai-decision-info');\\n        \\n        if (data.success && data.decision) {\\n            const decision = data.decision;\\n            infoDiv.innerHTML = `\\n                <div style=\\\"text-align: left;\\\">\\n                    <strong>Predicted BIT-TQ:</strong> ${decision.predicted_bit_tq.toFixed(1)} dmm<br>\\n                    <strong>Confidence:</strong> ${(decision.confidence * 100).toFixed(0)}%<br>\\n                    <strong>Energy Saving:</strong> ${(decision.predicted_energy_saving * 100).toFixed(1)}%<br>\\n                    <strong>CO2 Reduction:</strong> ${(decision.predicted_co2_reduction * 100).toFixed(1)}%\\n                </div>\\n            `;\\n            document.getElementById('apply-ai-btn').disabled = false;\\n        } else {\\n            infoDiv.innerHTML = '<em>No pending AI decisions</em>';\\n            document.getElementById('apply-ai-btn').disabled = true;\\n        }\\n    } catch (error) {\\n        console.error('Error loading AI decision:', error);\\n        document.getElementById('ai-decision-info').innerHTML = '<em>API connection failed</em>';\\n    }\\n}\\n\\nasync function applyAIDecision() {\\n    const btn = document.getElementById('apply-ai-btn');\\n    const statusDiv = document.getElementById('status-message');\\n    \\n    btn.disabled = true;\\n    btn.innerHTML = '⏳ Applying...';\\n    statusDiv.innerHTML = 'Applying AI optimization to OPC-UA server...';\\n    \\n    try {\\n        const response = await fetch(`${apiBaseUrl}/ai-decisions/apply`, {\\n            method: 'POST',\\n            headers: {\\n                'Content-Type': 'application/json'\\n            }\\n        });\\n        \\n        const data = await response.json();\\n        \\n        if (data.success) {\\n            statusDiv.innerHTML = `✅ AI decision applied successfully! Predicted BIT-TQ: ${data.predicted_bit_tq.toFixed(1)} dmm`;\\n            statusDiv.style.color = '#4CAF50';\\n            \\n            setTimeout(() => {\\n                loadLatestDecision();\\n                statusDiv.style.color = '#f0f0f0';\\n                statusDiv.innerHTML = 'AI optimization active - monitoring results...';\\n            }, 3000);\\n        } else {\\n            statusDiv.innerHTML = `❌ Failed: ${data.message}`;\\n            statusDiv.style.color = '#ff6b6b';\\n        }\\n    } catch (error) {\\n        statusDiv.innerHTML = `❌ Error: ${error.message}`;\\n        statusDiv.style.color = '#ff6b6b';\\n    } finally {\\n        btn.disabled = false;\\n        btn.innerHTML = '✨ Apply AI Decision';\\n        \\n        setTimeout(() => {\\n            statusDiv.style.color = '#f0f0f0';\\n        }, 5000);\\n    }\\n}\\n\\nasync function resetToHuman() {\\n    const btn = document.getElementById('reset-btn');\\n    const statusDiv = document.getElementById('status-message');\\n    \\n    btn.disabled = true;\\n    btn.innerHTML = '⏳ Resetting...';\\n    statusDiv.innerHTML = 'Resetting to human control...';\\n    \\n    try {\\n        const response = await fetch(`${apiBaseUrl}/process/reset`, {\\n            method: 'POST',\\n            headers: {\\n                'Content-Type': 'application/json'\\n            }\\n        });\\n        \\n        const data = await response.json();\\n        \\n        if (data.success) {\\n            statusDiv.innerHTML = '✅ Process reset to human control';\\n            statusDiv.style.color = '#4CAF50';\\n            \\n            setTimeout(() => {\\n                loadLatestDecision();\\n                statusDiv.style.color = '#f0f0f0';\\n                statusDiv.innerHTML = 'Ready for AI optimization';\\n            }, 3000);\\n        } else {\\n            statusDiv.innerHTML = `❌ Reset failed: ${data.message}`;\\n            statusDiv.style.color = '#ff6b6b';\\n        }\\n    } catch (error) {\\n        statusDiv.innerHTML = `❌ Error: ${error.message}`;\\n        statusDiv.style.color = '#ff6b6b';\\n    } finally {\\n        btn.disabled = false;\\n        btn.innerHTML = '🔄 Reset to Human';\\n        \\n        setTimeout(() => {\\n            statusDiv.style.color = '#f0f0f0';\\n        }, 5000);\\n    }\\n}\\n\\nloadLatestDecision();\\nsetInterval(loadLatestDecision, 10000);\\n</script>",
        "mode": "html"
      },
      "pluginVersion": "11.3.0",
      "title": "AI Control Panel",
      "type": "text"
    }
  ],
  "preload": false,
  "refresh": "5s",
  "schemaVersion": 41,
  "tags": ["demo", "ai", "refinery"],
  "templating": {
    "list": []
  },
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "timepicker": {},
  "timezone": "browser",
  "title": "Demo - Refinery AI Analytics Enhanced",
  "uid": "dashboard-demo-refinery-enhanced",
  "version": 1
}
EOF

# Update Docker Compose
echo "🐳 Updating docker-compose.yml..."

cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  timescaledb:
    image: timescale/timescaledb:latest-pg14
    container_name: demo-timescaledb
    environment:
      POSTGRES_DB: refinery_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - ./init_db.sql:/docker-entrypoint-initdb.d/init_db.sql
      - timescale_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 30s
      timeout: 10s
      retries: 3

  grafana:
    image: grafana/grafana:latest
    container_name: demo-grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_SECURITY_ALLOW_EMBEDDING: true
      GF_AUTH_ANONYMOUS_ENABLED: true
      GF_AUTH_ANONYMOUS_ORG_ROLE: Viewer
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana-config/provisioning:/etc/grafana/provisioning
    depends_on:
      - timescaledb

  opc-simulator:
    build: ./opc-simulator
    container_name: demo-opc-simulator
    ports:
      - "4840:4840"
    healthcheck:
      test: ["CMD-SHELL", "netstat -ln | grep :4840 || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3

  python-client:
    build: ./python-client
    container_name: demo-python-client
    depends_on:
      timescaledb:
        condition: service_healthy
      opc-simulator:
        condition: service_healthy
    environment:
      DB_HOST: timescaledb
      OPC_HOST: opc-simulator
      DB_USER: postgres
      DB_PASSWORD: password
      DB_NAME: refinery_db
    restart: unless-stopped

  api-server:
    build: ./api-server
    container_name: demo-api-server
    ports:
      - "5000:5000"
    depends_on:
      timescaledb:
        condition: service_healthy
      opc-simulator:
        condition: service_healthy
    environment:
      DB_HOST: timescaledb
      OPC_HOST: opc-simulator
      DB_USER: postgres
      DB_PASSWORD: password
      DB_NAME: refinery_db
      FLASK_ENV: production
    restart: unless-stopped

volumes:
  timescale_data:
  grafana_data:
EOF

# Update start script
echo "📝 Creating enhanced start script..."

cat > start-demo-enhanced.sh << 'EOF'
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
EOF

chmod +x start-demo-enhanced.sh

echo ""
echo "✅ Enhanced Demo setup completed!"
echo ""
echo "🚀 To start the enhanced demo:"
echo "   ./start-demo-enhanced.sh"
echo ""
echo "📋 What's new:"
echo "   • AI Control Panel with interactive buttons"
echo "   • Apply AI decisions directly from dashboard"
echo "   • Real-time BIT-TQ improvements"
echo "   • Process efficiency monitoring"
echo "   • Human vs AI control modes"
echo ""
echo "🎯 Demo flow:"
echo "   1. Wait for AI to generate recommendations"
echo "   2. Click 'Apply AI Decision' in dashboard"
echo "   3. Watch BIT-TQ jump from ~45 to 50+ dmm"
echo "   4. See energy savings and efficiency gains"