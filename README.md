# 🏭 Demo - Digital Twin and AI Analytics for Refinery

**Demo completa della PoC per raffineria**  
*Human vs AI Optimization - Mostra la differenza tra controllo manuale e AI*

## 🎯 Obiettivo della Demo

Dimostrare come l'AI ottimizzi il processo di raffinazione meglio dell'intervento umano:

- **KPI Principale**: Penetrazione bitume non flussato (BIT-TQ)
- **Risultati Attesi**: Da 45.2 → 52.1 dmm, -5% energia, -12% CO2  
- **ROI**: €27K/mese risparmio (€333K/anno)
- **Modello AI**: R²=0.77, 30 variabili, 4 parametri principali

## 🏗️ Architettura

```
OPC-UA Simulator ←→ Python Client + AI Mock ←→ TimescaleDB ←→ Grafana
```

- **OPC-UA Server**: Simula sensori raffineria (Node.js)
- **Python Client**: Legge dati, applica AI mock, scrive risultati
- **TimescaleDB**: Database time-series per storico dati
- **Grafana**: Dashboard real-time Human vs AI

## 🚀 Quick Start

### Prerequisiti
- Docker & Docker Compose
- 8GB RAM disponibili
- Porte libere: 3000, 4840, 5432

### Avvio Demo
```bash
# Clone o scarica i file
git clone <repo-url> demo-demo
cd demo-demo

# Avvia tutti i servizi
docker-compose up -d

# Monitora i log (opzionale)
docker-compose logs -f

# Aspetta 30 secondi per inizializzazione
sleep 30

# Apri Grafana Dashboard
open http://localhost:3000
# Login: admin / admin
```

### 🎬 Scenario Demo (5 minuti)

1. **Min 0-1**: Dashboard mostra situazione baseline (BIT-TQ ~45)
2. **Min 1-2**: Sistema rileva problema qualità  
3. **Min 2-3**: Simulazione "intervento umano" (risultato parziale)
4. **Min 3-4**: AI prende controllo → ottimizzazione multi-parametro
5. **Min 4-5**: Risultati finali: target raggiunto + risparmi energetici

### 📊 Dashboard Panels

- **🎯 BIT-TQ Monitor**: KPI principale in tempo reale
- **🤖 AI Status**: Confidence e decisioni attive  
- **💰 Savings**: Risparmi economici live
- **⚡ Energia**: Consumo vs efficienza
- **🌱 CO2**: Impatto ambientale
- **📊 Human vs AI**: Confronto performance
- **🚨 Anomalie**: Alert e correzioni automatiche
- **💡 AI Recommendations**: Suggerimenti in tempo reale

## 🔧 Componenti Dettagliati

### OPC-UA Simulator (Node.js)
```javascript
// Simula 11 parametri della raffineria
// Include scenari demo automatici
// Endpoint: opc.tcp://localhost:4840/refinery
```

**Parametri Simulati:**
- `fc1065`: Flow rate crude oil (127.3 ±2%)
- `li40054`: Level indicator (68.2 ±3%)  
- `fc31007`: Flow control HVbGO (89.1 ±2.5%)
- `pi18213`: Pressure (2.14 ±1%)
- `bit_tq`: Penetrazione bitume (45.2 ±4%) **← KPI principale**
- `energy_consumption`: Consumo (1250 ±5%)
- `co2_emissions`: Emissioni (34.5 ±4%)
- Plus: temperatura, flussi, stati sistema

### Python Client + AI Mock
```python
# Implementa modello simulato
# R² = 0.77, confidence 81%
# 4 parametri principali + interazioni
# Decisioni ogni 10 secondi
```

**Logica AI Mock:**
- Analizza correlazioni multi-variabili
- Ottimizzazioni simultanee (fc1065 +4.3%, li40054 +4.8%, etc.)
- Predice risultati: BIT-TQ, energia, CO2
- Calcola ROI economico

### Database Schema (TimescaleDB)
```sql
-- Tabelle principali
process_data      -- Dati tempo reale
ai_decisions      -- Decisioni e predizioni  
anomalies         -- Alert rilevati
human_vs_ai_performance  -- Confronti

-- Viste aggregate
dashboard_realtime
savings_calculator
```

## 📈 Risultati Demo

### Performance AI vs Human

| Metrica | Controllo Umano | AI | Miglioramento |
|---------|----------------|---------|---------------|
| **BIT-TQ (dmm)** | 48.1 | 52.1 | +8.3% |
| **Energia (MWh)** | +15% | -5% | 20% differenza |
| **CO2 (ton/h)** | +8% | -12% | 20% differenza |
| **Tempo decisione** | 15 min | 3 sec | 300x più veloce |
| **Parametri considerati** | 1-2 | 30+ | 15x più completo |

### ROI Economico

- **5% Improvement**: €27,781/mese → €333K/anno
- **10% Improvement**: €55,526/mese → €667K/anno  
- **Target PoC**: €5M+ annui su tutti i KPI

### Impatto Ambientale

- **CO2 evitata**: 15,000 ton/anno
- **Metano evitato**: 7,000 ton/anno
- **Efficienza energetica**: +10-15%

## 🎪 Punti Dimostrativi Chiave

### 1. **Complessità Nascosta**
```
UMANO VEDE: "BIT-TQ basso → abbassa temperatura"
AI VEDE: "30 variabili interconnesse, 
          4 parametri critici con interazioni non-lineari"
```

### 2. **Ottimizzazione Multi-Obiettivo**
```
APPROCCIO UMANO: Fix 1 problema, crea 2 effetti collaterali
APPROCCIO AI: Ottimizza simultaneamente qualità + energia + emissioni
```

### 3. **Velocità e Precisione**
```
UMANO: 15 min analisi → 1 parametro → 50% accuratezza
AI: 3 sec analisi → 12 parametri → 81% accuratezza
```

### 4. **Valore Economico**
```
Delta ROI: €19K/mese differenza = €228K/anno
Su UN SOLO KPI di 6 totali!
```

## 🔧 Troubleshooting

### Servizi non si avviano
```bash
# Verifica porte libere
netstat -tulpn | grep -E ':(3000|4840|5432)'

# Restart servizi
docker-compose down
docker-compose up -d
```

### Dashboard vuota
```bash
# Verifica Python client
docker-compose logs python-client

# Verifica database
docker-compose exec timescaledb psql -U postgres -d refinery_db -c "SELECT COUNT(*) FROM process_data;"
```

### OPC-UA connection error
```bash
# Restart OPC simulator
docker-compose restart opc-simulator
sleep 10
docker-compose restart python-client
```

## 🎨 Personalizzazione Demo

### Modifica Scenari
Edita `opc-simulator/server.js`:
```javascript
// Cambia timing scenari
setTimeout(() => {
    // Tuo scenario personalizzato
}, 45000); // 45 secondi
```

### Nuovi KPI
Aggiungi in `python-client/main_client.py`:
```python
# Nuovo parametro nel mock AI
'new_kpi': { value: 100, min: 80, max: 120, variance: 0.03 }
```

### Dashboard Panels
Modifica `grafana-config/provisioning/dashboards/demo-demo.json`

## 📞 Supporto

**Per problemi tecnici:**
- Verifica requisiti sistema
- Controlla log: `docker-compose logs`
- Restart: `docker-compose restart`

**Per modifiche demo:**
- Modifica timing in simulator
- Aggiungi KPI in Python client  
- Personalizza dashboard Grafana

## 🎯 Prossimi Passi

Dopo la demo di successo:

1. **Estensione KPI**: Aggiungere altri 5 KPI della PoC
2. **Modello Reale**: Sostituire mock con vero modello
3. **Integrazione**: Connessione a sistemi IP reali  
4. **Scaling**: Applicazione ad altri processi raffineria

---

**🏆 Questa demo dimostra concretamente perché l'AI supera il controllo umano tradizionale nella gestione di processi industriali complessi.**