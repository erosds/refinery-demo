-- Initialize demo Database
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Tabella dati di processo in tempo reale
CREATE TABLE process_data (
    timestamp TIMESTAMPTZ NOT NULL,
    fc1065 REAL,           -- Flow rate crude oil
    li40054 REAL,          -- Level indicator storage tank
    fc31007 REAL,          -- Flow control HVbGO
    pi18213 REAL,          -- Pressure fractionation column
    bit_tq REAL,           -- Penetrazione bitume non flussato (target KPI)
    energy_consumption REAL, -- Consumo energetico (MWh)
    co2_emissions REAL,    -- Emissioni CO2 (ton/h)
    hvbgo_flow REAL,       -- Flusso ricircolo HVbGO
    temperature_flash REAL, -- Temperatura zona flash
    process_efficiency REAL, -- Efficienza processo %
    data_source VARCHAR(20) DEFAULT 'opc_ua' -- Fonte dati
);

-- Converti in hypertable per performance time-series
SELECT create_hypertable('process_data', 'timestamp');

-- Tabella decisioni e predizioni AI
CREATE TABLE ai_decisions (
    timestamp TIMESTAMPTZ NOT NULL,
    decision_type VARCHAR(20) DEFAULT 'optimization', -- human, ai_suggestion, ai_applied
    confidence REAL,
    predicted_bit_tq REAL,
    predicted_energy_saving REAL,
    predicted_co2_reduction REAL,
    parameters_changed JSONB,      -- Parametri modificati dall'AI
    baseline_values JSONB,         -- Valori di partenza
    savings_eur_hour REAL,         -- Risparmi €/ora stimati
    anomaly_detected BOOLEAN DEFAULT FALSE,
    decision_applied BOOLEAN DEFAULT FALSE,
    operator_approved BOOLEAN DEFAULT NULL
);

SELECT create_hypertable('ai_decisions', 'timestamp');

-- Tabella anomalie rilevate
CREATE TABLE anomalies (
    timestamp TIMESTAMPTZ NOT NULL,
    anomaly_type VARCHAR(50),
    severity INTEGER,       -- 1-5 scala gravità
    parameter_name VARCHAR(20),
    normal_range_min REAL,
    normal_range_max REAL,
    actual_value REAL,
    deviation_percentage REAL,
    auto_resolved BOOLEAN DEFAULT FALSE
);

SELECT create_hypertable('anomalies', 'timestamp');

-- Vista aggregata per dashboard Grafana
CREATE VIEW dashboard_realtime AS
SELECT 
    timestamp,
    bit_tq,
    energy_consumption,
    co2_emissions,
    process_efficiency,
    hvbgo_flow,
    CASE 
        WHEN bit_tq < 48 THEN 'CRITICAL'
        WHEN bit_tq < 50 THEN 'WARNING' 
        WHEN bit_tq > 55 THEN 'OPTIMAL'
        ELSE 'NORMAL'
    END as status
FROM process_data 
WHERE timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;

-- Vista confronto Human vs AI performance
CREATE VIEW human_vs_ai_performance AS
WITH human_decisions AS (
    SELECT 
        DATE_TRUNC('hour', timestamp) as hour,
        AVG(bit_tq) as avg_bit_tq_human,
        AVG(energy_consumption) as avg_energy_human,
        AVG(co2_emissions) as avg_co2_human,
        COUNT(*) as human_datapoints
    FROM process_data 
    WHERE data_source = 'human_control'
    GROUP BY DATE_TRUNC('hour', timestamp)
),
ai_decisions AS (
    SELECT 
        DATE_TRUNC('hour', timestamp) as hour,
        AVG(bit_tq) as avg_bit_tq_ai,
        AVG(energy_consumption) as avg_energy_ai,
        AVG(co2_emissions) as avg_co2_ai,
        COUNT(*) as ai_datapoints
    FROM process_data 
    WHERE data_source = 'ai_control'
    GROUP BY DATE_TRUNC('hour', timestamp)
)
SELECT 
    COALESCE(h.hour, a.hour) as hour,
    h.avg_bit_tq_human,
    a.avg_bit_tq_ai,
    h.avg_energy_human,
    a.avg_energy_ai,
    h.avg_co2_human,
    a.avg_co2_ai,
    CASE 
        WHEN a.avg_bit_tq_ai > h.avg_bit_tq_human THEN 'AI_BETTER'
        WHEN h.avg_bit_tq_human > a.avg_bit_tq_ai THEN 'HUMAN_BETTER'
        ELSE 'TIE'
    END as performance_winner
FROM human_decisions h
FULL OUTER JOIN ai_decisions a ON h.hour = a.hour
ORDER BY hour DESC;

-- Vista savings calculator
CREATE VIEW savings_calculator AS
SELECT 
    DATE_TRUNC('day', timestamp) as day,
    SUM(savings_eur_hour) as daily_savings_eur,
    SUM(predicted_energy_saving * energy_baseline.avg_energy) as energy_saved_mwh,
    SUM(predicted_co2_reduction * co2_baseline.avg_co2) as co2_avoided_tons,
    COUNT(*) as ai_decisions_count
FROM ai_decisions a
CROSS JOIN (SELECT AVG(energy_consumption) as avg_energy FROM process_data WHERE timestamp > NOW() - INTERVAL '7 days') energy_baseline
CROSS JOIN (SELECT AVG(co2_emissions) as avg_co2 FROM process_data WHERE timestamp > NOW() - INTERVAL '7 days') co2_baseline
WHERE decision_applied = TRUE
GROUP BY DATE_TRUNC('day', timestamp)
ORDER BY day DESC;

-- Indici per performance
CREATE INDEX idx_process_data_timestamp ON process_data (timestamp DESC);
CREATE INDEX idx_ai_decisions_timestamp ON ai_decisions (timestamp DESC);
CREATE INDEX idx_process_data_bit_tq ON process_data (bit_tq);
CREATE INDEX idx_ai_decisions_applied ON ai_decisions (decision_applied, timestamp);

-- Inserimento dati di esempio per test
INSERT INTO process_data (timestamp, fc1065, li40054, fc31007, pi18213, bit_tq, energy_consumption, co2_emissions, hvbgo_flow, temperature_flash, process_efficiency) VALUES
(NOW() - INTERVAL '1 hour', 127.3, 68.2, 89.1, 2.14, 45.2, 1250.0, 34.5, 156.8, 420.0, 78.5),
(NOW() - INTERVAL '30 minutes', 128.1, 69.5, 90.2, 2.18, 46.8, 1280.0, 35.2, 158.2, 425.0, 79.2),
(NOW() - INTERVAL '15 minutes', 125.9, 67.8, 88.7, 2.12, 44.1, 1220.0, 33.8, 154.3, 415.0, 77.8);

-- Trigger per calcolo automatico efficienza
CREATE OR REPLACE FUNCTION calculate_efficiency()
RETURNS TRIGGER AS $$
BEGIN
    -- Calcola efficienza basata su bit_tq target e consumi energia
    NEW.process_efficiency := CASE 
        WHEN NEW.bit_tq >= 50 AND NEW.energy_consumption < 1300 THEN 85 + RANDOM() * 10
        WHEN NEW.bit_tq >= 45 THEN 75 + RANDOM() * 10  
        ELSE 65 + RANDOM() * 10
    END;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_calculate_efficiency
    BEFORE INSERT ON process_data
    FOR EACH ROW
    EXECUTE FUNCTION calculate_efficiency();