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
        
# Aggiungi questi endpoint al file api-server/app.py

@app.route('/api/process/current', methods=['GET'])
def get_current_process_data():
    """Endpoint per ottenere i dati attuali del processo"""
    try:
        conn = psycopg2.connect(**applier.db_config)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                bit_tq,
                energy_consumption,
                co2_emissions,
                process_efficiency,
                data_source,
                timestamp
            FROM process_data 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        if result:
            return jsonify({
                'success': True,
                'data': {
                    'bit_tq': result[0],
                    'energy_consumption': result[1],
                    'co2_emissions': result[2],
                    'process_efficiency': result[3],
                    'data_source': result[4],
                    'timestamp': result[5].isoformat() if result[5] else None,
                    'is_ai_control': result[4] == 'ai_control'
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
    finally:
        conn.close()

@app.route('/api/ai-decisions/force-generate', methods=['POST'])
def force_generate_ai_decision():
    """Endpoint per forzare la generazione di una decisione AI"""
    try:
        # Questo endpoint può essere chiamato per creare una decisione AI 
        # anche quando BIT-TQ è accettabile, utile per demo
        
        conn = psycopg2.connect(**applier.db_config)
        cursor = conn.cursor()
        
        # Ottieni dati attuali
        cursor.execute("""
            SELECT fc1065, li40054, fc31007, pi18213, bit_tq, energy_consumption, co2_emissions
            FROM process_data 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        if not result:
            return jsonify({
                'success': False,
                'message': 'No process data available'
            })
        
        # Simula una decisione AI
        from datetime import datetime
        import json
        
        # Crea parametri di ottimizzazione per demo
        current_bit_tq = result[4] or 45.0
        target_improvement = 55.0 - current_bit_tq if current_bit_tq < 55.0 else 2.0
        
        optimized_params = {
            'fc1065': (result[0] or 127.3) * 1.04,  # +4% 
            'li40054': (result[1] or 68.2) * 1.05,  # +5%
            'fc31007': (result[2] or 89.1) * 0.97,  # -3%
            'pi18213': (result[3] or 2.14) * 1.04   # +4%
        }
        
        baseline_params = {
            'fc1065': result[0] or 127.3,
            'li40054': result[1] or 68.2,
            'fc31007': result[2] or 89.1,
            'pi18213': result[3] or 2.14
        }
        
        predicted_bit_tq = min(58.0, current_bit_tq + target_improvement)
        energy_saving = 0.08  # 8% risparmio energetico
        co2_reduction = 0.12  # 12% riduzione CO2
        hourly_savings = 185.0  # €185/ora
        
        # Inserisci decisione forzata
        cursor.execute("""
            INSERT INTO ai_decisions (
                timestamp, decision_type, confidence, predicted_bit_tq,
                predicted_energy_saving, predicted_co2_reduction, 
                parameters_changed, baseline_values, savings_eur_hour,
                anomaly_detected, decision_applied
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            datetime.now(),
            'forced_optimization',
            0.82,  # 82% confidenza
            predicted_bit_tq,
            energy_saving,
            co2_reduction,
            json.dumps(optimized_params),
            json.dumps(baseline_params),
            hourly_savings,
            False,
            False  # Non ancora applicata
        ))
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'AI decision generated successfully',
            'decision': {
                'predicted_bit_tq': predicted_bit_tq,
                'energy_saving_pct': energy_saving * 100,
                'co2_reduction_pct': co2_reduction * 100,
                'hourly_savings_eur': hourly_savings,
                'confidence': 0.82,
                'parameters_count': len(optimized_params)
            }
        })
        
    except Exception as e:
        logger.error(f"Error forcing AI decision: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })
    finally:
        conn.close()

# Modifica anche l'endpoint di status per includere più informazioni
@app.route('/api/status', methods=['GET'])
def get_status():
    """Endpoint per lo status dettagliato dell'API"""
    try:
        # Test connessione database
        conn = psycopg2.connect(**applier.db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM process_data")
        data_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ai_decisions WHERE decision_applied = false")
        pending_decisions = cursor.fetchone()[0]
        
        cursor.execute("SELECT bit_tq FROM process_data ORDER BY timestamp DESC LIMIT 1")
        current_bit_tq = cursor.fetchone()
        current_bit_tq = current_bit_tq[0] if current_bit_tq else None
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'AI Decision API is running',
            'system_status': {
                'database_connected': True,
                'total_data_points': data_count,
                'pending_ai_decisions': pending_decisions,
                'current_bit_tq': current_bit_tq,
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
        return jsonify({
            'success': False,
            'message': f'API running but database error: {str(e)}',
            'system_status': {
                'database_connected': False,
                'error': str(e)
            }
        })

if __name__ == '__main__':
    logger.info("🚀 Starting AI Decision API Server...")
    app.run(host='0.0.0.0', port=5000, debug=False)
