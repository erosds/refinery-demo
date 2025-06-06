-- Initialize demo Database - VERSIONE CORRETTA
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

-- Tabella decisioni e predizioni AI - VERSIONE CORRETTA CON ID
CREATE TABLE ai_decisions (
    id SERIAL,             -- ID sequenziale per identificazione univoca
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

-- Crea hypertable per ai_decisions
SELECT create_hypertable('ai_decisions', 'timestamp');

-- Indici per performance - MIGLIORATI
CREATE INDEX idx_process_data_timestamp ON process_data (timestamp DESC);
CREATE INDEX idx_process_data_bit_tq ON process_data (bit_tq);
CREATE INDEX idx_process_data_source ON process_data (data_source, timestamp DESC);

-- Indici specifici per ai_decisions
CREATE INDEX idx_ai_decisions_timestamp ON ai_decisions (timestamp DESC);
CREATE INDEX idx_ai_decisions_applied ON ai_decisions (decision_applied, timestamp DESC);
CREATE INDEX idx_ai_decisions_id ON ai_decisions (id);
CREATE INDEX idx_ai_decisions_pending ON ai_decisions (decision_applied) WHERE decision_applied = false;

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

-- Vista aggregata per dashboard Grafana - MIGLIORATA
CREATE VIEW dashboard_realtime AS
SELECT 
    timestamp,
    bit_tq,
    energy_consumption,
    co2_emissions,
    process_efficiency,
    hvbgo_flow,
    data_source,
    CASE 
        WHEN bit_tq < 40 THEN 'CRITICAL'
        WHEN bit_tq < 45 THEN 'WARNING' 
        WHEN bit_tq < 50 THEN 'NORMAL'
        WHEN bit_tq >= 50 AND bit_tq < 55 THEN 'GOOD'
        WHEN bit_tq >= 55 THEN 'OPTIMAL'
        ELSE 'UNKNOWN'
    END as status,
    CASE 
        WHEN data_source = 'ai_control' THEN 'AI'
        WHEN data_source = 'human_control' THEN 'HUMAN'
        ELSE 'AUTO'
    END as control_mode
FROM process_data 
WHERE timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;

-- Vista confronto Human vs AI performance - MIGLIORATA
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
    AND timestamp > NOW() - INTERVAL '24 hours'
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
    AND timestamp > NOW() - INTERVAL '24 hours'
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
    END as performance_winner,
    CASE 
        WHEN a.avg_energy_ai < h.avg_energy_human THEN 'AI_MORE_EFFICIENT'
        WHEN h.avg_energy_human < a.avg_energy_ai THEN 'HUMAN_MORE_EFFICIENT'
        ELSE 'TIE'
    END as efficiency_winner
FROM human_decisions h
FULL OUTER JOIN ai_decisions a ON h.hour = a.hour
ORDER BY hour DESC;

-- Vista savings calculator - MIGLIORATA
CREATE VIEW savings_calculator AS
SELECT 
    DATE_TRUNC('day', timestamp) as day,
    SUM(savings_eur_hour) as daily_savings_eur,
    AVG(predicted_energy_saving) * 100 as avg_energy_saving_pct,
    AVG(predicted_co2_reduction) * 100 as avg_co2_reduction_pct,
    COUNT(*) as ai_decisions_count,
    COUNT(CASE WHEN decision_applied = true THEN 1 END) as applied_decisions,
    ROUND(
        COUNT(CASE WHEN decision_applied = true THEN 1 END)::REAL / 
        NULLIF(COUNT(*), 0) * 100, 2
    ) as application_rate_pct
FROM ai_decisions 
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', timestamp)
ORDER BY day DESC;

-- Vista AI decision summary per dashboard
CREATE VIEW ai_decision_summary AS
SELECT 
    COUNT(*) as total_decisions,
    COUNT(CASE WHEN decision_applied = true THEN 1 END) as applied_decisions,
    COUNT(CASE WHEN decision_applied = false THEN 1 END) as pending_decisions,
    AVG(confidence) as avg_confidence,
    AVG(predicted_bit_tq) as avg_predicted_bit_tq,
    SUM(savings_eur_hour) as total_hourly_savings,
    MAX(timestamp) as last_decision_time
FROM ai_decisions
WHERE timestamp > NOW() - INTERVAL '24 hours';

-- Inserimento dati di esempio per test - MIGLIORATI
INSERT INTO process_data (timestamp, fc1065, li40054, fc31007, pi18213, bit_tq, energy_consumption, co2_emissions, hvbgo_flow, temperature_flash, process_efficiency, data_source) VALUES
(NOW() - INTERVAL '2 hours', 127.3, 68.2, 89.1, 2.14, 45.2, 1250.0, 34.5, 156.8, 420.0, 78.5, 'human_control'),
(NOW() - INTERVAL '1 hour', 128.1, 69.5, 90.2, 2.18, 46.8, 1280.0, 35.2, 158.2, 425.0, 79.2, 'human_control'),
(NOW() - INTERVAL '30 minutes', 125.9, 67.8, 88.7, 2.12, 44.1, 1220.0, 33.8, 154.3, 415.0, 77.8, 'human_control');

-- Inserimento decisione AI di esempio
INSERT INTO ai_decisions (
    timestamp, decision_type, confidence, predicted_bit_tq,
    predicted_energy_saving, predicted_co2_reduction, 
    parameters_changed, baseline_values, savings_eur_hour,
    anomaly_detected, decision_applied
) VALUES (
    NOW() - INTERVAL '15 minutes',
    'demo_optimization',
    0.85,
    52.3,
    0.08,
    0.12,
    '{"fc1065": 132.0, "li40054": 71.2, "fc31007": 86.8, "pi18213": 2.22}',
    '{"fc1065": 127.3, "li40054": 68.2, "fc31007": 89.1, "pi18213": 2.14}',
    195.0,
    false,
    false
);

-- Trigger per calcolo automatico efficienza - MIGLIORATO
CREATE OR REPLACE FUNCTION calculate_efficiency()
RETURNS TRIGGER AS $$
BEGIN
    -- Calcola efficienza basata su bit_tq target e consumi energia
    NEW.process_efficiency := CASE 
        WHEN NEW.bit_tq >= 50 AND NEW.energy_consumption < 1300 THEN 85 + RANDOM() * 10
        WHEN NEW.bit_tq >= 45 AND NEW.energy_consumption < 1400 THEN 75 + RANDOM() * 10  
        WHEN NEW.bit_tq >= 40 THEN 65 + RANDOM() * 10
        ELSE 50 + RANDOM() * 15
    END;
    
    -- Assicura che l'efficienza sia realistica
    NEW.process_efficiency := GREATEST(30, LEAST(100, NEW.process_efficiency));
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_calculate_efficiency
    BEFORE INSERT ON process_data
    FOR EACH ROW
    EXECUTE FUNCTION calculate_efficiency();

-- Trigger per monitoraggio anomalie
CREATE OR REPLACE FUNCTION detect_anomalies()
RETURNS TRIGGER AS $$
BEGIN
    -- Rileva anomalie BIT-TQ
    IF NEW.bit_tq < 35 OR NEW.bit_tq > 65 THEN
        INSERT INTO anomalies (
            timestamp, anomaly_type, severity, parameter_name,
            normal_range_min, normal_range_max, actual_value,
            deviation_percentage
        ) VALUES (
            NEW.timestamp, 'BIT_TQ_OUT_OF_RANGE', 
            CASE WHEN NEW.bit_tq < 30 OR NEW.bit_tq > 70 THEN 5 ELSE 3 END,
            'bit_tq', 35, 65, NEW.bit_tq,
            ABS(NEW.bit_tq - 50) / 50 * 100
        );
    END IF;
    
    -- Rileva anomalie energia
    IF NEW.energy_consumption > 1500 THEN
        INSERT INTO anomalies (
            timestamp, anomaly_type, severity, parameter_name,
            normal_range_min, normal_range_max, actual_value,
            deviation_percentage
        ) VALUES (
            NEW.timestamp, 'HIGH_ENERGY_CONSUMPTION', 2,
            'energy_consumption', 1000, 1400, NEW.energy_consumption,
            (NEW.energy_consumption - 1250) / 1250 * 100
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_detect_anomalies
    AFTER INSERT ON process_data
    FOR EACH ROW
    EXECUTE FUNCTION detect_anomalies();

-- Funzione di pulizia dati vecchi (retention policy)
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Mantieni solo 30 giorni di dati processo dettagliati
    DELETE FROM process_data WHERE timestamp < NOW() - INTERVAL '30 days';
    
    -- Mantieni 90 giorni di decisioni AI
    DELETE FROM ai_decisions WHERE timestamp < NOW() - INTERVAL '90 days';
    
    -- Mantieni 7 giorni di anomalie
    DELETE FROM anomalies WHERE timestamp < NOW() - INTERVAL '7 days';
    
    RAISE NOTICE 'Cleanup completed at %', NOW();
END;
$$ LANGUAGE plpgsql;

-- Informazioni di sistema
INSERT INTO process_data (timestamp, fc1065, li40054, fc31007, pi18213, bit_tq, energy_consumption, co2_emissions, hvbgo_flow, temperature_flash, process_efficiency, data_source) 
VALUES (NOW(), 127.3, 68.2, 89.1, 2.14, 45.2, 1250.0, 34.5, 156.8, 420.0, 78.5, 'human_control');

-- Log finale
DO $$
BEGIN
    RAISE NOTICE '✅ Demo Database initialized successfully!';
    RAISE NOTICE '📊 Tables created: process_data, ai_decisions, anomalies';
    RAISE NOTICE '🔍 Views created: dashboard_realtime, human_vs_ai_performance, savings_calculator, ai_decision_summary';
    RAISE NOTICE '⚡ Triggers created: efficiency calculation, anomaly detection';
    RAISE NOTICE '🧪 Sample data inserted for testing';
    RAISE NOTICE '🚀 System ready for AI-powered refinery optimization!';
END $$;