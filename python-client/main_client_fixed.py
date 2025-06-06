"""
Demo Demo - Python Client with AI Mock (ENHANCED VERSION)
Versione migliorata con generazione più affidabile di decisioni AI
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
    """Mock del modello AI basato sui risultati della PoC - VERSIONE MIGLIORATA"""
    
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
        self.last_decision_time = 0
        self.min_decision_interval = 30  # Minimo 30 secondi tra decisioni
        
    def analyze_current_state(self, data: Dict) -> Dict:
        bit_tq = data.get('bit_tq', 45.0)
        analysis = {
            'needs_optimization': bit_tq < self.bit_tq_target,
            'current_bit_tq': bit_tq,
            'target_bit_tq': self.bit_tq_target,
            'anomaly_detected': bit_tq < 40 or bit_tq > 60,
            'deviation_percentage': ((self.bit_tq_target - bit_tq) / self.bit_tq_target) * 100 if self.bit_tq_target > 0 else 0,
            'urgency_level': self._calculate_urgency(bit_tq)
        }
        return analysis
    
    def _calculate_urgency(self, bit_tq: float) -> str:
        """Calcola il livello di urgenza basato su BIT-TQ"""
        if bit_tq < 40:
            return 'CRITICAL'
        elif bit_tq < 45:
            return 'HIGH'
        elif bit_tq < 48:
            return 'MEDIUM'
        elif bit_tq < 50:
            return 'LOW'
        else:
            return 'NORMAL'
    
    def should_generate_decision(self, current_data: Dict) -> bool:
        """Determina se dovrebbe generare una decisione AI"""
        current_time = time.time()
        time_since_last = current_time - self.last_decision_time
        
        # Non generare troppo frequentemente
        if time_since_last < self.min_decision_interval:
            return False
        
        analysis = self.analyze_current_state(current_data)
        
        # Criteri per generazione decisione:
        # 1. BIT-TQ sotto target
        # 2. Anomalia rilevata
        # 3. Ogni 2 minuti se in stato non ottimale
        should_generate = (
            analysis['needs_optimization'] or
            analysis['anomaly_detected'] or
            (time_since_last > 120 and analysis['urgency_level'] != 'NORMAL')
        )
        
        return should_generate
    
    def generate_optimization_decision(self, current_data: Dict) -> Optional[Dict]:
        """Genera decisione di ottimizzazione AI - VERSIONE MIGLIORATA"""
        if not self.should_generate_decision(current_data):
            return None
            
        analysis = self.analyze_current_state(current_data)
        
        logger.info(f"🤖 AI Analysis: BIT-TQ {analysis['current_bit_tq']:.1f} → Target {analysis['target_bit_tq']} (Urgency: {analysis['urgency_level']})")
        
        optimizations = {}
        for param in self.primary_features:
            current_value = current_data.get(param, self._get_default_value(param))
            optimal_min, optimal_max = self.optimal_ranges[param]
            weight = self.feature_weights[param]
            
            # Calcola aggiustamenti basati su urgenza
            urgency_multiplier = self._get_urgency_multiplier(analysis['urgency_level'])
            
            if param == 'fc1065':
                adjustment = 0.043 * weight * urgency_multiplier
                new_value = current_value * (1 + adjustment)
            elif param == 'li40054':
                adjustment = 0.048 * weight * urgency_multiplier
                new_value = current_value * (1 + adjustment)
            elif param == 'fc31007':
                adjustment = 0.027 * weight * urgency_multiplier
                new_value = current_value * (1 - adjustment)
            elif param == 'pi18213':
                adjustment = 0.037 * weight * urgency_multiplier
                new_value = current_value * (1 + adjustment)
            
            new_value = max(optimal_min, min(optimal_max, new_value))
            optimizations[param] = round(new_value, 3)
        
        bit_tq_improvement = self._predict_bit_tq_improvement(current_data, optimizations)
        predicted_bit_tq = current_data.get('bit_tq', 45.0) + bit_tq_improvement
        
        energy_saving_pct = min(0.12, bit_tq_improvement * 0.025)
        co2_reduction_pct = min(0.15, bit_tq_improvement * 0.03)
        
        # Calcola risparmi basati su miglioramento effettivo
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
                'bit_tq': round(predicted_bit_tq, 2),
                'energy_saving_pct': round(energy_saving_pct, 3),
                'co2_reduction_pct': round(co2_reduction_pct, 3),
                'hvbgo_flow_reduction': round(bit_tq_improvement * 2.5, 2)
            },
            'economic_impact': {
                'hourly_savings_eur': max(0, round(hourly_savings, 2)),
                'monthly_savings_eur': max(0, round(monthly_savings, 2)),
                'annual_potential_eur': max(0, round(monthly_savings * 12, 2))
            }
        }
        
        self.last_decision_time = time.time()
        
        logger.info(f"💡 AI Decision Generated: {len(optimizations)} parameters, €{hourly_savings:.0f}/h savings, confidence {decision['confidence']:.2f}")
        return decision
    
    def _get_urgency_multiplier(self, urgency_level: str) -> float:
        """Restituisce il moltiplicatore basato sull'urgenza"""
        multipliers = {
            'CRITICAL': 1.5,
            'HIGH': 1.2,
            'MEDIUM': 1.0,
            'LOW': 0.8,
            'NORMAL': 0.5
        }
        return multipliers.get(urgency_level, 1.0)
    
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
        
        # Aggiungi rumore realistico
        noise = np.random.normal(0, max(0.1, total_improvement * 0.23))
        return max(0, total_improvement + noise)


class RefineryDataClient:
    """Client principale per connessione OPC-UA e gestione dati - VERSIONE MIGLIORATA"""
    
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
        self.cycle_count = 0
        
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
        """Legge dati dal server OPC-UA con fallback robusto"""
        data = {}
        
        try:
            self.opc_client.set_session_timeout(10000)
            self.opc_client.set_security_string("None")
            
            await self.opc_client.connect()
            logger.debug("🔗 OPC-UA connected successfully")
            
            root = self.opc_client.get_root_node()
            objects = await root.get_child(["0:Objects"])
            children = await objects.get_children()
            
            refinery_node = None
            for child in children:
                display_name = await child.read_display_name()
                if "Refinery" in str(display_name):
                    refinery_node = child
                    break
            
            if refinery_node:
                variables = await refinery_node.get_children()
                
                for var in variables:
                    try:
                        browse_name = await var.read_browse_name()
                        var_name = str(browse_name.Name)
                        value = await var.read_value()
                        data[var_name] = float(value)
                        
                    except Exception as e:
                        logger.debug(f"⚠️ Failed to read {var_name}: {e}")
                        
                if len(data) > 5 and data.get('bit_tq', 0) > 0:
                    logger.debug(f"✅ Successfully read {len(data)} OPC variables")
                else:
                    logger.warning("⚠️ Insufficient valid data, using fallback")
                    data = self.fallback_data.copy()
                    
            else:
                logger.warning("⚠️ Refinery node not found, using fallback")
                data = self.fallback_data.copy()
                
        except Exception as e:
            logger.debug(f"⚠️ OPC connection failed: {e}, using fallback")
            data = self.fallback_data.copy()
            
        finally:
            try:
                await self.opc_client.disconnect()
            except:
                pass
        
        # Apply realistic variations to fallback data
        if len(data) <= len(self.fallback_data):
            for key in data:
                if key not in ['system_status', 'operator_mode']:
                    variance = 0.02 if 'bit_tq' in key else 0.01
                    data[key] = data[key] * (1 + (np.random.random() - 0.5) * variance)
                    
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
            
            # Log solo ogni 5 cicli per ridurre verbosity
            if self.cycle_count % 5 == 0:
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
                False  # Always start as not applied
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
    
    def _check_pending_decisions(self):
        """Verifica se ci sono decisioni AI in attesa di applicazione"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM ai_decisions 
                WHERE decision_applied = false 
                AND timestamp > NOW() - INTERVAL '10 minutes'
            """)
            result = cursor.fetchone()
            return result[0] > 0 if result else False
        except Exception as e:
            logger.error(f"Error checking pending decisions: {e}")
            return False

    async def run_demo_cycle(self):
        """Ciclo principale della demo con generazione affidabile di decisioni AI"""
        logger.info("🎬 Starting Enhanced Demo Cycle...")
        
        while True:
            try:
                self.cycle_count += 1
                
                # Log dettagliato ogni 10 cicli
                if self.cycle_count % 10 == 1:
                    logger.info(f"🔄 Demo Cycle #{self.cycle_count}")
                
                current_data = await self.read_opc_data()
                current_bit_tq = current_data.get('bit_tq', 45.0)
                
                # Determina data source basato su operator_mode
                data_source = 'ai_control' if current_data.get('operator_mode') == 1 else 'human_control'
                self.store_process_data(current_data, data_source)
                
                # Log status ogni 20 cicli
                if self.cycle_count % 20 == 1:
                    logger.info(f"📊 Current BIT-TQ: {current_bit_tq:.1f}, Mode: {data_source}")
                
                # Verifica se dovrebbe generare decisione AI
                should_generate = self.ai_model.should_generate_decision(current_data)
                
                if should_generate:
                    # Verifica se ci sono già decisioni pendenti
                    pending_decisions = self._check_pending_decisions()
                    
                    if not pending_decisions:
                        ai_decision = self.ai_model.generate_optimization_decision(current_data)
                        if ai_decision:
                            self.store_ai_decision(ai_decision)
                            logger.info("✅ New AI decision generated and stored")
                            
                            # Log dettagli della decisione
                            urgency = ai_decision['analysis']['urgency_level']
                            predicted_improvement = ai_decision['predictions']['bit_tq'] - current_bit_tq
                            logger.info(f"🎯 Predicted improvement: +{predicted_improvement:.1f} BIT-TQ (Urgency: {urgency})")
                        else:
                            logger.debug("ℹ️ AI model decided not to generate decision")
                    else:
                        if self.cycle_count % 20 == 1:
                            logger.info("ℹ️ AI decision pending application, skipping new generation")
                else:
                    if self.cycle_count % 30 == 1:
                        logger.debug("ℹ️ No need for AI decision at this time")
                
                # Sleep dinamico basato su urgenza
                sleep_time = self._get_sleep_time(current_bit_tq)
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"❌ Demo cycle error: {e}")
                await asyncio.sleep(10)

    def _get_sleep_time(self, bit_tq: float) -> int:
        """Calcola tempo di sleep basato su urgenza"""
        if bit_tq < 40:
            return 10  # Modalità critica: cicli più frequenti
        elif bit_tq < 45:
            return 15  # Modalità alta urgenza
        elif bit_tq < 50:
            return 20  # Modalità normale
        else:
            return 25  # Modalità rilassata


async def main():
    """Funzione principale"""
    client = RefineryDataClient()
    
    try:
        await client.initialize()
        logger.info("⏳ Waiting for OPC-UA server startup...")
        await asyncio.sleep(20)
        
        logger.info("🚀 Starting enhanced demo cycle with improved AI decision generation")
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