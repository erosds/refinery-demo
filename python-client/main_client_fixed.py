"""
Demo Demo - Python Client with AI Mock (FIXED VERSION)
Fixes OPC-UA connection and data reading issues
"""

import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
from asyncua import Client, ua
import json
import time
import os
import logging
from datetime import datetime
import numpy as np
from typing import Dict, Optional, Tuple

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AIMock:
    """Mock del modello AI basato sui risultati della PoC"""
    
    def __init__(self):
        self.model_confidence = 0.77
        self.primary_features = ['fc1065', 'li40054', 'fc31007', 'pi18213']
        self.bit_tq_target = 50.0
        self.optimal_ranges = {
            'fc1065': (125, 135), 'li40054': (65, 75),
            'fc31007': (85, 95), 'pi18213': (2.1, 2.3)
        }
        self.feature_weights = {
            'fc1065': 0.5321, 'li40054': 0.4250,
            'fc31007': 0.4399, 'pi18213': 0.3159
        }
        
    def analyze_current_state(self, data: Dict) -> Dict:
        bit_tq = data.get('bit_tq', 45.0)
        analysis = {
            'needs_optimization': bit_tq < self.bit_tq_target,
            'current_bit_tq': bit_tq,
            'target_bit_tq': self.bit_tq_target,
            'anomaly_detected': bit_tq < 40 or bit_tq > 60,
            'deviation_percentage': ((self.bit_tq_target - bit_tq) / self.bit_tq_target) * 100 if self.bit_tq_target > 0 else 0
        }
        return analysis
    
    def generate_optimization_decision(self, current_data: Dict) -> Optional[Dict]:
        analysis = self.analyze_current_state(current_data)
        
        if not analysis['needs_optimization'] and not analysis['anomaly_detected']:
            return None
            
        logger.info(f"🤖 AI Analysis: BIT-TQ {analysis['current_bit_tq']:.1f} → Target {analysis['target_bit_tq']}")
        
        optimizations = {}
        for param in self.primary_features:
            current_value = current_data.get(param, self._get_default_value(param))
            optimal_min, optimal_max = self.optimal_ranges[param]
            weight = self.feature_weights[param]
            
            if param == 'fc1065':
                new_value = current_value * (1 + 0.043 * weight)
            elif param == 'li40054':
                new_value = current_value * (1 + 0.048 * weight)
            elif param == 'fc31007':
                new_value = current_value * (1 - 0.027 * weight)
            elif param == 'pi18213':
                new_value = current_value * (1 + 0.037 * weight)
            
            new_value = max(optimal_min, min(optimal_max, new_value))
            optimizations[param] = new_value
        
        bit_tq_improvement = self._predict_bit_tq_improvement(current_data, optimizations)
        predicted_bit_tq = current_data.get('bit_tq', 45.0) + bit_tq_improvement
        
        energy_saving_pct = min(0.10, bit_tq_improvement * 0.02)
        co2_reduction_pct = min(0.15, bit_tq_improvement * 0.025)
        
        monthly_savings_base = 27781
        improvement_factor = max(0.01, bit_tq_improvement / (self.bit_tq_target * 0.05))
        monthly_savings = monthly_savings_base * improvement_factor
        hourly_savings = monthly_savings / (30 * 24)
        
        decision = {
            'timestamp': datetime.now().isoformat(),
            'decision_type': 'ai_optimization',
            'confidence': min(1.0, max(0.5, self.model_confidence + np.random.normal(0, 0.05))),
            'analysis': analysis,
            'parameter_changes': optimizations,
            'baseline_values': {param: current_data.get(param, self._get_default_value(param)) for param in self.primary_features},
            'predictions': {
                'bit_tq': predicted_bit_tq,
                'energy_saving_pct': energy_saving_pct,
                'co2_reduction_pct': co2_reduction_pct,
                'hvbgo_flow_reduction': bit_tq_improvement * 2.5
            },
            'economic_impact': {
                'hourly_savings_eur': max(0, hourly_savings),
                'monthly_savings_eur': max(0, monthly_savings),
                'annual_potential_eur': max(0, monthly_savings * 12)
            }
        }
        
        logger.info(f"💡 AI Decision: {len(optimizations)} parameters, €{hourly_savings:.0f}/h savings")
        return decision
    
    def _get_default_value(self, param: str) -> float:
        defaults = {'fc1065': 127.3, 'li40054': 68.2, 'fc31007': 89.1, 'pi18213': 2.14, 'bit_tq': 45.2}
        return defaults.get(param, 1.0)
    
    def _predict_bit_tq_improvement(self, current_data: Dict, optimizations: Dict) -> float:
        total_improvement = 0
        for param, new_value in optimizations.items():
            current_value = current_data.get(param, self._get_default_value(param))
            if current_value == 0:
                current_value = self._get_default_value(param)
            change_pct = (new_value - current_value) / current_value if current_value > 0 else 0
            weight = self.feature_weights[param]
            contribution = change_pct * weight * 15
            total_improvement += contribution
        noise = np.random.normal(0, max(0.1, total_improvement * 0.23))
        return max(0, total_improvement + noise)


class RefineryDataClient:
    """Client principale per connessione OPC-UA e gestione dati"""
    
    def __init__(self):
        self.opc_url = f"opc.tcp://{os.getenv('OPC_HOST', 'localhost')}:4840/refinery"
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'refinery_db'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'password'),
            'port': 5432
        }
        
        self.ai_model = AIMock()
        self.db_conn = None
        self.opc_client = None
        self.fallback_data = {
            'fc1065': 127.3, 'li40054': 68.2, 'fc31007': 89.1, 'pi18213': 2.14,
            'bit_tq': 45.2, 'energy_consumption': 1250, 'co2_emissions': 34.5,
            'hvbgo_flow': 156.8, 'temperature_flash': 420.0, 'system_status': 1,
            'operator_mode': 0
        }
        
    async def initialize(self):
        """Inizializza connessioni"""
        try:
            self.db_conn = psycopg2.connect(**self.db_config)
            logger.info("✅ Connected to TimescaleDB")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
            
        self.opc_client = Client(self.opc_url)
        logger.info(f"🔗 OPC-UA client configured for {self.opc_url}")
        
    async def read_opc_data(self) -> Dict:
        """Legge dati dal server OPC-UA con fallback robusto - VERSIONE FISSATA"""
        data = {}
        
        try:
            self.opc_client.set_session_timeout(10000)
            self.opc_client.set_security_string("None")
            
            await self.opc_client.connect()
            logger.info("🔗 OPC-UA connected successfully")
            
            root = self.opc_client.get_root_node()
            objects = await root.get_child(["0:Objects"])
            children = await objects.get_children()
            
            refinery_node = None
            for child in children:
                display_name = await child.read_display_name()
                if "Refinery" in str(display_name):
                    refinery_node = child
                    logger.info(f"✅ Found Refinery node: {display_name}")
                    break
            
            if refinery_node:
                variables = await refinery_node.get_children()
                logger.info(f"📊 Found {len(variables)} variables in Refinery node")
                
                for var in variables:
                    try:
                        browse_name = await var.read_browse_name()
                        var_name = str(browse_name.Name)
                        value = await var.read_value()
                        data[var_name] = float(value)
                        
                        if var_name in ['bit_tq', 'energy_consumption', 'fc1065']:
                            logger.info(f"  📈 {var_name}: {value}")
                            
                    except Exception as e:
                        logger.warning(f"⚠️  Failed to read {var_name}: {e}")
                        
                if len(data) > 5 and data.get('bit_tq', 0) > 0:
                    logger.info(f"✅ Successfully read {len(data)} OPC variables")
                else:
                    logger.warning("⚠️  Insufficient valid data, using fallback")
                    data = self.fallback_data.copy()
                    
            else:
                logger.warning("⚠️  Refinery node not found, using fallback")
                data = self.fallback_data.copy()
                
        except Exception as e:
            logger.warning(f"⚠️  OPC connection failed: {e}, using fallback")
            data = self.fallback_data.copy()
            
        finally:
            try:
                await self.opc_client.disconnect()
            except:
                pass
        
        # Apply realistic variations to fallback data
        if len(data) <= len(self.fallback_data) and 'bit_tq' in data and data['bit_tq'] == self.fallback_data['bit_tq']:
            for key in data:
                if key not in ['system_status', 'operator_mode']:
                    variance = 0.02 if 'bit_tq' in key else 0.01
                    data[key] = data[key] * (1 + (np.random.random() - 0.5) * variance)
            logger.info("🎲 Applied realistic variations to fallback data")
                    
        return data
    
    def store_process_data(self, data: Dict, data_source: str = 'opc_ua'):
        """Salva dati di processo in TimescaleDB"""
        try:
            cursor = self.db_conn.cursor()
            process_efficiency = self._calculate_process_efficiency(data)
            
            cursor.execute("""
                INSERT INTO process_data (
                    timestamp, fc1065, li40054, fc31007, pi18213, bit_tq,
                    energy_consumption, co2_emissions, hvbgo_flow, 
                    temperature_flash, process_efficiency, data_source
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                datetime.now(),
                data.get('fc1065'), data.get('li40054'), data.get('fc31007'),
                data.get('pi18213'), data.get('bit_tq'), data.get('energy_consumption'),
                data.get('co2_emissions'), data.get('hvbgo_flow'), 
                data.get('temperature_flash'), process_efficiency, data_source
            ))
            
            self.db_conn.commit()
            logger.info(f"💾 Stored process data: BIT-TQ {data.get('bit_tq', 0):.1f}")
            
        except Exception as e:
            logger.error(f"❌ Database insert error: {e}")
            self.db_conn.rollback()
    
    def store_ai_decision(self, decision: Dict):
        """Salva decisione AI in database"""
        try:
            cursor = self.db_conn.cursor()
            
            cursor.execute("""
                INSERT INTO ai_decisions (
                    timestamp, decision_type, confidence, predicted_bit_tq,
                    predicted_energy_saving, predicted_co2_reduction, 
                    parameters_changed, baseline_values, savings_eur_hour,
                    anomaly_detected, decision_applied
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                datetime.now(),
                decision['decision_type'],
                decision['confidence'],
                decision['predictions']['bit_tq'],
                decision['predictions']['energy_saving_pct'],
                decision['predictions']['co2_reduction_pct'],
                json.dumps(decision['parameter_changes']),
                json.dumps(decision['baseline_values']),
                decision['economic_impact']['hourly_savings_eur'],
                decision['analysis']['anomaly_detected'],
                True
            ))
            
            self.db_conn.commit()
            logger.info(f"💾 AI decision stored: €{decision['economic_impact']['hourly_savings_eur']:.0f}/h impact")
            
        except Exception as e:
            logger.error(f"❌ AI decision storage error: {e}")
            self.db_conn.rollback()
    
    def _calculate_process_efficiency(self, data: Dict) -> float:
        """Calcola efficienza processo basata su KPI"""
        bit_tq = data.get('bit_tq', 45)
        energy = data.get('energy_consumption', 1250)
        bit_tq_efficiency = min(100, (bit_tq / 50.0) * 100) if bit_tq > 0 else 0
        energy_efficiency = max(0, 100 - ((energy - 1200) / 10)) if energy > 0 else 0
        return (bit_tq_efficiency + energy_efficiency) / 2
    
    # Sostituisci il metodo run_demo_cycle in python-client/main_client_fixed.py
    # con questa versione che genera più decisioni AI:

    async def run_demo_cycle(self):
        """Ciclo principale della demo con più decisioni AI"""
        logger.info("🎬 Starting Enhanced Demo Cycle...")
        cycle_count = 0
        last_ai_decision_time = 0
        
        while True:
            try:
                cycle_count += 1
                logger.info(f"🔄 Demo Cycle #{cycle_count}")
                
                current_data = await self.read_opc_data()
                current_bit_tq = current_data.get('bit_tq', 45.0)
                logger.info(f"📊 Current BIT-TQ: {current_bit_tq:.1f}")
                
                data_source = 'ai_control' if current_data.get('operator_mode') == 1 else 'human_control'
                self.store_process_data(current_data, data_source)
                
                # Genera decisioni AI più frequentemente per la demo
                current_time = time.time()
                
                # Condizioni per generare decisione AI:
                # 1. BIT-TQ sotto target (< 50)
                # 2. Ogni 60 secondi se non ci sono decisioni pendenti
                # 3. Se rilevata anomalia
                should_generate_decision = (
                    current_bit_tq < 50.0 or  # Sotto target
                    current_bit_tq < 40 or current_bit_tq > 60 or  # Anomalia
                    (current_time - last_ai_decision_time) > 60  # Ogni minuto
                )
                
                if should_generate_decision:
                    # Verifica se ci sono decisioni pendenti
                    pending_decisions = self._check_pending_decisions()
                    
                    if not pending_decisions:
                        ai_decision = self.ai_model.generate_optimization_decision(current_data)
                        if ai_decision:
                            self.store_ai_decision(ai_decision)
                            last_ai_decision_time = current_time
                            logger.info("✅ New AI decision generated and stored")
                            
                            # Se BIT-TQ è molto basso, suggerisci applicazione immediata
                            if current_bit_tq < 45:
                                logger.warning("⚠️ BIT-TQ critically low! Consider applying AI decision immediately.")
                    else:
                        logger.info("ℹ️ AI decision pending application, skipping new generation")
                else:
                    logger.info("ℹ️ BIT-TQ within acceptable range, monitoring...")
                
                await asyncio.sleep(15)
                
            except Exception as e:
                logger.error(f"❌ Demo cycle error: {e}")
                await asyncio.sleep(10)

    def _check_pending_decisions(self):
        """Verifica se ci sono decisioni AI in attesa di applicazione"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM ai_decisions 
                WHERE decision_applied = false 
                AND timestamp > NOW() - INTERVAL '5 minutes'
            """)
            result = cursor.fetchone()
            return result[0] > 0 if result else False
        except Exception as e:
            logger.error(f"Error checking pending decisions: {e}")
            return False


async def main():
    """Funzione principale"""
    client = RefineryDataClient()
    
    try:
        await client.initialize()
        logger.info("⏳ Waiting for OPC-UA server startup...")
        await asyncio.sleep(20)
        await client.run_demo_cycle()
        
    except KeyboardInterrupt:
        logger.info("👋 Demo stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
    finally:
        if client.db_conn:
            client.db_conn.close()
            logger.info("🔌 Database connection closed")


if __name__ == "__main__":
    asyncio.run(main())
