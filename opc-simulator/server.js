const opcua = require("node-opcua");

console.log("🏭 Starting demo OPC-UA Refinery Simulator...");

// Configurazione server OPC-UA
const server = new opcua.OPCUAServer({
    port: 4840,
    resourcePath: "/refinery",
    buildInfo: {
        productName: "demo Refinery Simulator",
        buildNumber: "1.0.0",
        buildDate: new Date()
    }
});

// Variabili simulate della raffineria
let refineryData = {
    // Parametri di processo principali (da documenti PoC)
    fc1065: { value: 127.3, min: 120, max: 140, variance: 0.02 },     // Flow rate crude oil
    li40054: { value: 68.2, min: 60, max: 80, variance: 0.03 },       // Level indicator storage
    fc31007: { value: 89.1, min: 80, max: 100, variance: 0.025 },     // Flow control HVbGO  
    pi18213: { value: 2.14, min: 2.0, max: 2.5, variance: 0.01 },     // Pressure fractionation
    
    // KPI principale (dalla PoC)
    bit_tq: { value: 45.2, min: 35, max: 65, variance: 0.04 },        // Penetrazione bitume non flussato
    
    // Metriche operative
    energy_consumption: { value: 1250.0, min: 1000, max: 1500, variance: 0.05 },
    co2_emissions: { value: 34.5, min: 25, max: 45, variance: 0.04 },
    hvbgo_flow: { value: 156.8, min: 140, max: 180, variance: 0.03 },  // Flusso ricircolo HVbGO
    temperature_flash: { value: 420.0, min: 400, max: 450, variance: 0.02 },
    
    // Stati sistema
    system_status: { value: 1, min: 0, max: 3, variance: 0 },          // 0=off, 1=normal, 2=warning, 3=critical
    operator_mode: { value: 0, min: 0, max: 1, variance: 0 },          // 0=human, 1=ai
    last_ai_decision: { value: 0, min: 0, max: 1, variance: 0 }        // 0=none, 1=applied
};

// Variabili OPC-UA
let opcVariables = {};

function initializeServer() {
    server.initialize(() => {
        console.log("✅ OPC-UA Server initialized");
        
        // Crea namespace per la raffineria
        const addressSpace = server.engine.addressSpace;
        const namespace = addressSpace.getOwnNamespace();
        
        // Device principale della raffineria
        const refineryDevice = namespace.addObject({
            organizedBy: addressSpace.rootFolder.objects,
            browseName: "Refinery"
        });
        
        // Crea variabili OPC-UA per ogni parametro
        Object.keys(refineryData).forEach(paramName => {
            opcVariables[paramName] = namespace.addVariable({
                componentOf: refineryDevice,
                browseName: paramName,
                dataType: "Double",
                value: {
                    get: () => new opcua.Variant({
                        dataType: opcua.DataType.Double,
                        value: refineryData[paramName].value
                    }),
                    set: (variant) => {
                        console.log(`📝 Parameter ${paramName} set to: ${variant.value}`);
                        refineryData[paramName].value = variant.value;
                        return opcua.StatusCodes.Good;
                    }
                }
            });
        });
        
        console.log(`📊 Created ${Object.keys(opcVariables).length} OPC-UA variables`);
        startServer();
    });
}

function startServer() {
    server.start(() => {
        console.log("🚀 demo OPC-UA Server started on port 4840");
        console.log("📡 Endpoint: opc.tcp://localhost:4840/refinery");
        console.log("🔄 Simulating refinery data...");
        
        // Avvia simulazione dati
        startDataSimulation();
        
        // Simula scenari specifici per la demo
        startDemoScenarios();
    });
}

function startDataSimulation() {
    setInterval(() => {
        Object.keys(refineryData).forEach(param => {
            const data = refineryData[param];
            
            if (param === 'system_status' || param === 'operator_mode' || param === 'last_ai_decision') {
                return; // Skip status variables in normal simulation
            }
            
            // Variazione realistica basata su variance
            const variance = (Math.random() - 0.5) * 2 * data.variance;
            let newValue = data.value * (1 + variance);
            
            // Mantieni nei limiti
            newValue = Math.max(data.min, Math.min(data.max, newValue));
            
            // Correlazioni realistiche (dalla PoC: fc1065 influenza bit_tq)
            if (param === 'bit_tq') {
                const fc1065_influence = (refineryData.fc1065.value - 127.3) * 0.1;
                const li40054_influence = (refineryData.li40054.value - 68.2) * 0.08;
                newValue += fc1065_influence + li40054_influence;
            }
            
            if (param === 'energy_consumption') {
                // Energia correlata a flusso ricircolo
                const hvbgo_influence = (refineryData.hvbgo_flow.value - 156.8) * 2.5;
                newValue += hvbgo_influence;
            }
            
            if (param === 'co2_emissions') {
                // CO2 correlata a consumo energia
                const energy_ratio = refineryData.energy_consumption.value / 1250.0;
                newValue = 34.5 * energy_ratio + (Math.random() - 0.5) * 2;
            }
            
            refineryData[param].value = newValue;
        });
        
    }, 3000); // Aggiorna ogni 3 secondi (come specificato nella PoC)
}

function startDemoScenarios() {
    console.log("🎬 Starting demo scenarios...");
    
    // Scenario 1: Problema iniziale (BIT-TQ sotto target)
    setTimeout(() => {
        console.log("⚠️  Demo: Creating BIT-TQ problem (below 50 target)");
        refineryData.bit_tq.value = 44.5;
        refineryData.energy_consumption.value = 1320;
        refineryData.system_status.value = 2; // Warning
    }, 10000);
    
    // Scenario 2: Tentativo correzione umana (parziale)
    setTimeout(() => {
        console.log("👨‍🔧 Demo: Human operator adjusts temperature");
        refineryData.temperature_flash.value = 410; // -10°C
        refineryData.bit_tq.value = 48.1; // Miglioramento parziale
        refineryData.energy_consumption.value = 1380; // Ma energia aumenta!
        refineryData.operator_mode.value = 0; // Human control
    }, 30000);
    
    // Scenario 3: Intervento AI (ottimizzazione completa)
    setTimeout(() => {
        console.log("🤖 Demo: AI takes control - multi-parameter optimization");
        
        // Applica decisioni AI (dal documento PoC)
        refineryData.fc1065.value = 132.8;  // +4.3%
        refineryData.li40054.value = 71.5;   // +4.8%
        refineryData.fc31007.value = 86.7;   // -2.7%  
        refineryData.pi18213.value = 2.22;   // +3.7%
        
        // Risultati migliorati
        refineryData.bit_tq.value = 52.1;           // Target raggiunto
        refineryData.energy_consumption.value = 1188; // -5% energia
        refineryData.co2_emissions.value = 30.4;    // -12% CO2
        refineryData.hvbgo_flow.value = 148.5;      // Ricircolo ridotto
        
        refineryData.operator_mode.value = 1;       // AI control
        refineryData.last_ai_decision.value = 1;    // Decision applied
        refineryData.system_status.value = 1;       // Back to normal
        
    }, 60000);
    
    // Scenario 4: Anomalia rilevata e corretta dall'AI
    setTimeout(() => {
        console.log("🚨 Demo: Anomaly detected and auto-corrected by AI");
        
        // Simula spike anomalo (dai 202 rilevati nella PoC)
        refineryData.bit_tq.value = 38.2; // Anomalia
        refineryData.system_status.value = 3; // Critical
        
        // AI corregge rapidamente
        setTimeout(() => {
            refineryData.bit_tq.value = 51.5;
            refineryData.system_status.value = 1;
            console.log("✅ Demo: AI auto-correction successful");
        }, 5000);
        
    }, 120000);
}

// Gestione graceful shutdown
process.on('SIGINT', () => {
    console.log("\n🛑 Shutting down OPC-UA server...");
    server.shutdown(() => {
        console.log("✅ Server shutdown complete");
        process.exit(0);
    });
});

// Error handling
server.on("post_initialize", () => {
    console.log("🔧 Server post-initialization complete");
});

server.on("error", (err) => {
    console.error("❌ Server error:", err);
});

// Avvia il server
initializeServer();