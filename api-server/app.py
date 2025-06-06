"""
API Server per TimescaleDB - Gestisce hypertable senza PRIMARY KEY
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
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
    
    def ensure_id_column_exists(self):
        """Assicura che la colonna ID esista (non PRIMARY KEY per TimescaleDB)"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Controlla se la colonna id esiste
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='ai_decisions' AND column_name='id'
            """)
            
            if not cursor.fetchone():
                logger.info("Adding missing ID column to ai_decisions hypertable...")
                # Per TimescaleDB hypertable, aggiungi solo SERIAL (non PRIMARY KEY)
                cursor.execute("ALTER TABLE ai_decisions ADD COLUMN id SERIAL")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_decisions_id ON ai_decisions(id)")
                conn.commit()
                logger.info("✅ ID column added successfully")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error ensuring ID column exists: {e}")
        
    def get_latest_ai_decision(self) -> Optional[Dict]:
        """Recupera l'ultima decisione AI non ancora applicata"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Query per TimescaleDB hypertable - usa timestamp come identificatore principale
            cursor.execute("""
                SELECT 
                    COALESCE(id, EXTRACT(EPOCH FROM timestamp)::BIGINT) as id,
                    timestamp,
                    parameters_changed, 
                    predicted_bit_tq,
                    predicted_energy_saving,
                    predicted_co2_reduction,
                    confidence,
                    savings_eur_hour,
                    decision_applied,
                    decision_type
                FROM ai_decisions 
                WHERE (decision_applied = false OR decision_applied IS NULL)
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                logger.info(f"Found AI decision: ID={result['id']}, timestamp={result['timestamp']}")
                return {
                    'id': result['id'],
                    'timestamp': result['timestamp'],
                    'parameters_changed': json.loads(result['parameters_changed']) if result['parameters_changed'] else {},
                    'predicted_bit_tq': result['predicted_bit_tq'],
                    'predicted_energy_saving': result['predicted_energy_saving'],
                    'predicted_co2_reduction': result['predicted_co2_reduction'],
                    'confidence': result['confidence'],
                    'savings_eur_hour': result['savings_eur_hour'],
                    'decision_applied': result['decision_applied'],
                    'decision_type': result.get('decision_type', 'optimization')
                }
            else:
                logger.info("No pending AI decisions found")
                return None
            
        except Exception as e:
            logger.error(f"Error getting latest AI decision: {e}")
            return None
    
    def get_current_process_data(self) -> Optional[Dict]:
        """Recupera i dati attuali del processo dal database"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT 
                    bit_tq,
                    energy_consumption,
                    co2_emissions,
                    process_efficiency,
                    data_source,
                    timestamp,
                    fc1065,
                    li40054,
                    fc31007,
                    pi18213
                FROM process_data 
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Error getting current process data: {e}")
            return None
    
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
                await client.disconnect()
                return False
            
            # Applica i parametri
            variables = await refinery_node.get_children()
            applied_count = 0
            
            for var in variables:
                browse_name = await var.read_browse_name()
                var_name = str(browse_name.Name)
                
                if var_name in parameters:
                    try:
                        new_value = float(parameters[var_name])
                        await var.write_value(new_value)
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
    
    def mark_decision_as_applied(self, decision_timestamp):
        """Marca la decisione come applicata usando il timestamp (chiave naturale per hypertable)"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Per TimescaleDB hypertable, usa timestamp come identificatore
            cursor.execute("""
                UPDATE ai_decisions 
                SET decision_applied = true, operator_approved = true
                WHERE timestamp = %s
            """, (decision_timestamp,))
            
            rows_affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            if rows_affected > 0:
                logger.info(f"✅ Decision marked as applied (timestamp: {decision_timestamp})")
                return True
            else:
                logger.warning("⚠️ No decision was marked as applied")
                return False
            
        except Exception as e:
            logger.error(f"Error marking decision as applied: {e}")
            return False

# Inizializza l'applier
applier = AIDecisionApplier()

@app.route('/api/process/current', methods=['GET'])
def get_current_process_data():
    """Endpoint per ottenere i dati attuali del processo"""
    try:
        data = applier.get_current_process_data()
        
        if data:
            return jsonify({
                'success': True,
                'data': {
                    'bit_tq': data['bit_tq'],
                    'energy_consumption': data['energy_consumption'],
                    'co2_emissions': data['co2_emissions'],
                    'process_efficiency': data['process_efficiency'],
                    'data_source': data['data_source'],
                    'timestamp': data['timestamp'].isoformat() if data['timestamp'] else None,
                    'is_ai_control': data['data_source'] == 'ai_control',
                    'fc1065': data.get('fc1065'),
                    'li40054': data.get('li40054'),
                    'fc31007': data.get('fc31007'),
                    'pi18213': data.get('pi18213')
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No process data found'
            })
            
    except Exception as e:
        logger.error(f"Error getting current process data: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@app.route('/api/ai-decisions/latest', methods=['GET'])
def get_latest_decision():
    """Endpoint per ottenere l'ultima decisione AI"""
    try:
        decision = applier.get_latest_ai_decision()
        
        if decision:
            return jsonify({
                'success': True,
                'decision': decision,
                'message': f'Decisione AI trovata (timestamp: {decision["timestamp"]})'
            })
        else:
            # Conta il totale delle decisioni per debug
            try:
                conn = psycopg2.connect(**applier.db_config)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM ai_decisions")
                total_decisions = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM ai_decisions WHERE decision_applied = false OR decision_applied IS NULL")
                pending_decisions = cursor.fetchone()[0]
                
                conn.close()
                
                return jsonify({
                    'success': False,
                    'message': f'No pending AI decisions found. Total: {total_decisions}, Pending: {pending_decisions}',
                    'total_decisions': total_decisions,
                    'pending_decisions': pending_decisions
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'No decisions found and could not query database: {str(e)}'
                })
            
    except Exception as e:
        logger.error(f"Error in get_latest_decision: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
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
        
        logger.info(f"Applying AI decision: {decision['timestamp']}")
        
        # Applica i parametri
        success = asyncio.run(applier.apply_ai_parameters(decision['parameters_changed']))
        
        if success:
            # Marca come applicata usando il timestamp
            mark_success = applier.mark_decision_as_applied(decision['timestamp'])
            
            return jsonify({
                'success': True,
                'message': 'AI decision applied successfully',
                'applied_parameters': decision['parameters_changed'],
                'predicted_bit_tq': decision['predicted_bit_tq'],
                'confidence': decision['confidence'],
                'decision_id': decision['id'],
                'timestamp': decision['timestamp'].isoformat(),
                'marked_as_applied': mark_success
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

@app.route('/api/ai-decisions/force-generate', methods=['POST'])
def force_generate_ai_decision():
    """Endpoint per forzare la generazione di una decisione AI - per TimescaleDB"""
    try:
        # Assicura che la colonna ID esista (non PRIMARY KEY)
        applier.ensure_id_column_exists()
        
        current_data = applier.get_current_process_data()
        if not current_data:
            return jsonify({
                'success': False,
                'message': 'No process data available to generate AI decision'
            })
        
        current_bit_tq = current_data['bit_tq'] or 45.0
        target_improvement = max(2.0, 52.0 - current_bit_tq)
        
        # Parametri di ottimizzazione basati sui dati attuali
        optimized_params = {
            'fc1065': (current_data.get('fc1065') or 127.3) * 1.04,
            'li40054': (current_data.get('li40054') or 68.2) * 1.05,
            'fc31007': (current_data.get('fc31007') or 89.1) * 0.97,
            'pi18213': (current_data.get('pi18213') or 2.14) * 1.04
        }
        
        baseline_params = {
            'fc1065': current_data.get('fc1065') or 127.3,
            'li40054': current_data.get('li40054') or 68.2,
            'fc31007': current_data.get('fc31007') or 89.1,
            'pi18213': current_data.get('pi18213') or 2.14
        }
        
        predicted_bit_tq = min(58.0, current_bit_tq + target_improvement)
        energy_saving = 0.08
        co2_reduction = 0.12
        hourly_savings = 185.0
        
        # Inserisci decisione nel database (senza RETURNING per TimescaleDB)
        conn = psycopg2.connect(**applier.db_config)
        cursor = conn.cursor()
        
        decision_timestamp = datetime.now()
        
        cursor.execute("""
            INSERT INTO ai_decisions (
                timestamp, decision_type, confidence, predicted_bit_tq,
                predicted_energy_saving, predicted_co2_reduction, 
                parameters_changed, baseline_values, savings_eur_hour,
                anomaly_detected, decision_applied
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            decision_timestamp,
            'forced_optimization',
            0.82,
            predicted_bit_tq,
            energy_saving,
            co2_reduction,
            json.dumps(optimized_params),
            json.dumps(baseline_params),
            hourly_savings,
            current_bit_tq < 45.0,
            False
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Forced AI decision generated at: {decision_timestamp}")
        
        return jsonify({
            'success': True,
            'message': f'AI decision generated successfully',
            'decision_timestamp': decision_timestamp.isoformat(),
            'decision': {
                'predicted_bit_tq': predicted_bit_tq,
                'energy_saving_pct': energy_saving * 100,
                'co2_reduction_pct': co2_reduction * 100,
                'hourly_savings_eur': hourly_savings,
                'confidence': 0.82,
                'parameters_count': len(optimized_params),
                'current_bit_tq': current_bit_tq
            }
        })
        
    except Exception as e:
        logger.error(f"Error forcing AI decision: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@app.route('/api/status', methods=['GET'])
def get_status():
    """Endpoint per lo status dettagliato dell'API"""
    try:
        conn = psycopg2.connect(**applier.db_config)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM process_data")
        data_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ai_decisions WHERE decision_applied = false OR decision_applied IS NULL")
        pending_decisions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ai_decisions")
        total_decisions = cursor.fetchone()[0]
        
        # Ottieni dati processo attuali
        current_data = applier.get_current_process_data()
        current_bit_tq = current_data['bit_tq'] if current_data else None
        current_source = current_data['data_source'] if current_data else None
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'AI Decision API is running',
            'system_status': {
                'database_connected': True,
                'database_type': 'TimescaleDB hypertable',
                'total_data_points': data_count,
                'pending_ai_decisions': pending_decisions,
                'total_ai_decisions': total_decisions,
                'current_bit_tq': current_bit_tq,
                'current_data_source': current_source,
                'is_ai_control': current_source == 'ai_control' if current_source else False,
                'last_check': datetime.now().isoformat()
            },
            'endpoints': [
                '/api/ai-decisions/latest',
                '/api/ai-decisions/apply',
                '/api/ai-decisions/force-generate',
                '/api/process/current',
                '/api/process/reset',
                '/api/status'
            ]
        })
        
    except Exception as e:
        logger.error(f"Error in status endpoint: {e}")
        return jsonify({
            'success': False,
            'message': f'API running but database error: {str(e)}',
            'system_status': {
                'database_connected': False,
                'error': str(e)
            }
        })

if __name__ == '__main__':
    logger.info("🚀 Starting AI Decision API Server for TimescaleDB...")
    app.run(host='0.0.0.0', port=5000, debug=True)