"""
demo Demo - Python Client with AI Mock (FIXED VERSION)
Simula il modello per la demo della PoC
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
    """
    Mock del modello AI basato sui risultati della PoC
    R² = 0.77, modello a 30 variabili, 4 parametri principali
    """
    
    def __init__(self):
        # Parametri dal documento PoC - modello con R²=0.77
        self.model_confidence = 0.77
        self.primary_features = ['fc1065', 'li40054', 'fc31007', 'pi18213']
        
        # Target e range operativi dalla PoC
        self.bit_tq_target = 50.0
        self.optimal_ranges = {
            'fc1065': (125, 135),    # Flow rate crude oil
            'li40054': (65, 75),     # Level indicator  
            'fc31007': (85, 95),     # Flow control HVbGO
            'pi18213': (2.1, 2.3),   # Pressure
        }
        
        # Coefficienti di correlazione (simulati dalla PoC)
        self.feature_weights = {
            'fc1065': 0.5321,   # Sobol Total index
            'li40054': 0.4250,
            'fc31007': 0.4399, 
            'pi18213': 0.3159
        }
        
    def analyze_current_state(self, data: Dict) -> Dict:
        """Analizza lo stato attuale e determina se serve intervento"""
        bit_tq = data.get('bit_tq', 45.0)
        
        analysis = {
            'needs_optimization': bit_tq < self.bit_tq_target,
            'current_bit_tq': bit_tq,
            'target_bit_tq': self.bit_tq_target,
            'anomaly_detected': False,
            'deviation_percentage': ((self.bit_tq_target - bit_tq) / self.bit_tq_target) * 100 if self.bit_tq_target > 0 else 0
        }
        
        # Rileva anomalie (pattern dai 202 casi della PoC)
        if bit_tq < 40 or bit_tq > 60:
            analysis['anomaly_detected'] = True
            analysis['anomaly_severity'] = 'HIGH' if bit_tq < 35 or bit_tq > 65 else 'MEDIUM'
            
        return analysis
    
    def generate_optimization_decision(self, current_data: Dict) -> Optional[Dict]:
        """
        Genera decisione di ottimizzazione multi-parametrica
        Simula la logica AI complessa basata sui risultati PoC
        """
        analysis = self.analyze_current_state(current_data)
        
        if not analysis['needs_optimization'] and not analysis['anomaly_detected']:
            return None
            
        logger.info(f"🤖 AI Analysis: BIT-TQ {analysis['current_bit_tq']:.1f} → Target {analysis['target_bit_tq']}")
        
        # Calcola ottimizzazioni basate sui pesi delle feature
        optimizations = {}
        
        for param in self.primary_features:
            current_value = current_data.get(param, 0)
            if current_value == 0:  # FIX: Evita divisione per zero
                current_value = self._get_default_value(param)
                
            optimal_min, optimal_max = self.optimal_ranges[param]
            weight = self.feature_weights[param]
            
            # Calcola nuovo valore ottimale
            if param == 'fc1065':  # Flow rate crude - aumenta per migliorare BIT-TQ
                new_value = current_value * (1 + 0.043 * weight)  # +4.3% dalla PoC
            elif param == 'li40054':  # Level indicator - aumenta
                new_value = current_value * (1 + 0.048 * weight)  # +4.8%
            elif param == 'fc31007':  # Flow control - riduci per meno ricircolo
                new_value = current_value * (1 - 0.027 * weight)  # -2.7%
            elif param == 'pi18213':  # Pressure - aumenta leggermente
                new_value = current_value * (1 + 0.037 * weight)  # +3.7%
            
            # Mantieni nei range sicuri
            new_value = max(optimal_min, min(optimal_max, new_value))
            optimizations[param] = new_value
        
        # Predici risultato finale (simulazione modello R²=0.77)
        bit_tq_improvement = self._predict_bit_tq_improvement(current_data, optimizations)
        predicted_bit_tq = current_data.get('bit_tq', 45.0) + bit_tq_improvement
        
        # Calcola benefici energetici e ambientali
        energy_saving_pct = min(0.10, bit_tq_improvement * 0.02)  # Max 10% saving
        co2_reduction_pct = min(0.15, bit_tq_improvement * 0.025)  # Max 15% reduction
        
        # Calcola risparmi economici (€27K/mese dalla PoC per 5% improvement)
        monthly_savings_base = 27781  # €/mese per 5% improvement
        improvement_factor = max(0.01, bit_tq_improvement / (self.bit_tq_target * 0.05))  # FIX: Min value
        monthly_savings = monthly_savings_base * improvement_factor
        hourly_savings = monthly_savings / (30 * 24)
        
        decision = {
            'timestamp': datetime.now().isoformat(),
            'decision_type': 'ai_optimization',
            'confidence': min(1.0, max(0.5, self.model_confidence + np.random.normal(0, 0.05))),  # FIX: Limiti
            'analysis': analysis,
            'parameter_changes': optimizations,
            'baseline_values': {param: current_data.get(param, self._get_default_value(param)) for param in self.primary_features},
            'predictions': {
                'bit_tq': predicted_bit_tq,
                'energy_saving_pct': energy_saving_pct,
                'co2_reduction_pct': co2_reduction_pct,
                'hvbgo_flow_reduction': bit_tq_improvement * 2.5  # Riduzione flusso ricircolo
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
        """Valori di default per evitare errori"""
        defaults = {
            'fc1065': 127.3,
            'li40054': 68.2,
            'fc31007': 89.1,
            'pi18213': 2.14,
            'bit_tq': 45.2
        }
        return defaults.get(param, 1.0)
    
    def _predict_bit_tq_improvement(self, current_data: Dict, optimizations: Dict) -> float:
        """Simula predizione del modello AI per miglioramento BIT-TQ"""
        total_improvement = 0
        
        for param, new_value in optimizations.items():
            current_value = current_data.get(param, self._get_default_value(param))
            if current_value == 0:
                current_value = self._get_default_value(param)
                
            change_pct = (new_value - current_value) / current_value if current_value > 0 else 0
            weight = self.feature_weights[param]
            
            # Contributo non-lineare al miglioramento (simula complessità modello)
            contribution = change_pct * weight * 15  # Fattore di scala
            total_improvement += contribution
            
        # Aggiungi rumore realistico (R²=0.77 significa 23% di variabilità)
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
        self.demo_mode = True  # Modalità demo con scenari automatici
        self.fallback_data = {
            'fc1065': 127.3, 'li40054': 68.2, 'fc31007': 89.1, 'pi18213': 2.14,
            'bit_tq': 45.2, 'energy_consumption': 1250, 'co2_emissions': 34.5,
            'hvbgo_flow': 156.8, 'temperature_flash': 420.0, 'system_status': 1,
            'operator_mode': 0
        }
        
    async def initialize(self):
        """Inizializza connessioni"""
        # Database connection
        try:
            self.db_conn = psycopg2.connect(**self.db_config)
            logger.info("✅ Connected to TimescaleDB")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
            
        # OPC-UA client
        self.opc_client = Client(self.opc_url)
        logger.info(f"🔗 OPC-UA client configured for {self.opc_url}")
        
    async def debug_opc_structure(self):
        """Debug OPC-UA server structure"""
        try:
            await self.opc_client.connect()
            logger.info("🔍 Connected to OPC server, browsing structure...")
            
            root_node = self.opc_client.get_root_node()
            objects_node = await root_node.get_child(["0:Objects"])
            
            # Lista tutti i nodi sotto Objects
            children = await objects_node.get_children()
            logger.info(f"📋 Found {len(children)} nodes under Objects:")
            
            for child in children:
                display_name = await child.read_display_name()
                browse_name = await child.read_browse_name()
                logger.info(f"  - {display_name} (browse: {browse_name})")
                
                # Se trova un nodo che contiene dati della raffineria
                try:
                    grandchildren = await child.get_children()
                    if len(grandchildren) > 5:  # Probabilmente il nodo con le variabili
                        logger.info(f"    🎯 Found {len(grandchildren)} variables in {display_name}")
                        for var in grandchildren[:5]:  # Mostra prime 5
                            var_name = await var.read_browse_name()
                            try:
                                value = await var.read_value()
                                logger.info(f"      - {var_name}: {value}")
                            except:
                                logger.info(f"      - {var_name}: (read failed)")
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"❌ OPC debug failed: {e}")
        finally:
            try:
                await self.opc_client.disconnect()
            except:
                pass

        
    async def read_opc_data(self) -> Dict:
        """Legge dati dal server OPC-UA con fallback robusto"""
        data = {}
        
        try:
            await self.opc_client.connect()
            
            # Lista parametri da leggere (dal simulator)
            parameters = [
                'fc1065', 'li40054', 'fc31007', 'pi18213', 'bit_tq',
                'energy_consumption', 'co2_emissions', 'hvbgo_flow', 
                'temperature_flash', 'system_status', 'operator_mode'
            ]
            
            # Metodo semplificato per leggere variabili
            root_node = self.opc_client.get_root_node()
            objects_node = await root_node.get_child(["0:Objects"])
            
            try:
                # Cerca il nodo della raffineria
                children = await objects_node.get_children()
                refinery_node = None
                
                for child in children:
                    display_name = await child.read_display_name()
                    if "Refinery" in str(display_name) or "Refinery" in str(display_name):
                        refinery_node = child
                        break
                
                if refinery_node:
                    var_children = await refinery_node.get_children()
                    for var_node in var_children:
                        browse_name = await var_node.read_browse_name()
                        var_name = str(browse_name).split(":")[-1]  # Estrai nome variabile
                        
                        if var_name in parameters:
                            try:
                                value = await var_node.read_value()
                                data[var_name] = float(value)
                            except:
                                data[var_name] = self.fallback_data.get(var_name, 0)
                else:
                    logger.warning("⚠️  Refinery node not found, using fallback data")
                    data = self.fallback_data.copy()
                    
            except Exception as e:
                logger.warning(f"⚠️  OPC structure navigation failed: {e}")
                data = self.fallback_data.copy()
                
        except Exception as e:
            logger.warning(f"⚠️  OPC-UA connection failed: {e}, using fallback")
            data = self.fallback_data.copy()
            
        finally:
            try:
                await self.opc_client.disconnect()
            except:
                pass
        
        # Simula variazioni realistiche sui dati fallback
        if data == self.fallback_data:
            for key in data:
                if key not in ['system_status', 'operator_mode']:
                    variance = 0.02 if 'bit_tq' in key else 0.01
                    data[key] = data[key] * (1 + (np.random.random() - 0.5) * variance)
                    
        return data
    
    async def read_opc_data_improved(self) -> Dict:
        """Lettura OPC migliorata con debug"""
        data = {}
        
        try:
            await self.opc_client.connect()
            logger.info("🔗 OPC connected, searching for data nodes...")
            
            root_node = self.opc_client.get_root_node()
            objects_node = await root_node.get_child(["0:Objects"])
            children = await objects_node.get_children()
            
            # Cerca il nodo con più variabili (probabilmente il nostro)
            best_node = None
            max_vars = 0
            
            for child in children:
                try:
                    vars_count = len(await child.get_children())
                    if vars_count > max_vars:
                        max_vars = vars_count
                        best_node = child
                except:
                    continue
            
            if best_node:
                logger.info(f"📊 Using node with {max_vars} variables")
                var_children = await best_node.get_children()
                
                for var_node in var_children:
                    try:
                        browse_name = await var_node.read_browse_name()
                        var_name = str(browse_name).split(":")[-1]
                        value = await var_node.read_value()
                        data[var_name] = float(value)
                        logger.info(f"✅ {var_name}: {value}")
                    except Exception as e:
                        logger.warning(f"⚠️  Failed to read {var_name}: {e}")
            
            if not data:
                logger.warning("⚠️  No data found, using fallback")
                data = self.fallback_data.copy()
                
        except Exception as e:
            logger.warning(f"⚠️  OPC connection failed: {e}")
            data = self.fallback_data.copy()
        finally:
            try:
                await self.opc_client.disconnect()
            except:
                pass
        
        # Applica variazioni realistiche ai dati fallback
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
            
            # Calcola efficienza processo
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
                True  # Applied automatically in demo
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
        
        # Efficienza basata su prossimità al target e consumo energia
        bit_tq_efficiency = min(100, (bit_tq / 50.0) * 100) if bit_tq > 0 else 0
        energy_efficiency = max(0, 100 - ((energy - 1200) / 10)) if energy > 0 else 0
        
        return (bit_tq_efficiency + energy_efficiency) / 2
    
    async def run_demo_cycle(self):
        """Ciclo principale della demo"""
        logger.info("🎬 Starting demo Demo Cycle...")
        
        cycle_count = 0
        
        while True:
            try:
                cycle_count += 1
                logger.info(f"🔄 Demo Cycle #{cycle_count}")
                
                # 1. Leggi dati attuali
                current_data = await self.read_opc_data()
                logger.info(f"📊 Current BIT-TQ: {current_data.get('bit_tq', 0):.1f}")
                
                # 2. Salva dati processo
                data_source = 'ai_control' if current_data.get('operator_mode') == 1 else 'human_control'
                self.store_process_data(current_data, data_source)
                
                # 3. Analisi AI
                ai_decision = self.ai_model.generate_optimization_decision(current_data)
                
                if ai_decision:
                    # 4. Salva decisione AI
                    self.store_ai_decision(ai_decision)
                    logger.info("✅ AI decision processed")
                
                # Sleep per prossimo ciclo
                await asyncio.sleep(10)  # Ogni 10 secondi
                
            except Exception as e:
                logger.error(f"❌ Demo cycle error: {e}")
                await asyncio.sleep(5)


async def main():
    """Funzione principale"""
    client = RefineryDataClient()
    
    try:
        # Inizializza connessioni
        await client.initialize()
        
        # Attendi che OPC server sia pronto
        logger.info("⏳ Waiting for OPC-UA server...")
        await asyncio.sleep(15)
        
        # Avvia ciclo demo
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