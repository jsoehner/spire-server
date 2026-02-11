#!/bin/bash

# --- Configuration ---
SETUP_SCRIPT="setup_demo_v9.py"
AGENT_SCRIPT="add_agent-v4.py"
SETUP_DIR="spire_setup"

# --- Functions ---

# Function to check if a Python script exists
check_script() {
    if [ ! -f "$1" ]; then
        echo "❌ Error: Could not find '$1'."
        echo "   Please make sure you have saved the latest python script as '$1'."
        exit 1
    fi
}

# --- Execution ---

echo "=========================================="
echo "   🚀 Starting SPIRE HA Demo Automation   "
echo "=========================================="

# 1. Run the Infrastructure Setup (Server + DB + LB)
check_script "$SETUP_SCRIPT"
echo "Step 1: Running Infrastructure Setup ($SETUP_SCRIPT)..."
python3 "$SETUP_SCRIPT"

if [ $? -ne 0 ]; then
    echo "❌ Error: $SETUP_SCRIPT failed."
    exit 1
fi

echo "✅ Infrastructure setup complete."
echo "⏳ Waiting 15 seconds for Postgres and SPIRE Server to stabilize..."
sleep 15

# 2. Register the Agent
check_script "$AGENT_SCRIPT"
echo "Step 2: Registering Agent ($AGENT_SCRIPT)..."
python3 "$AGENT_SCRIPT"

if [ $? -ne 0 ]; then
    echo "❌ Error: $AGENT_SCRIPT failed."
    exit 1
fi

echo "✅ Agent registered and started."

# 3. Validation & Logs
echo "=========================================="
echo "   🎉 Demo is Running!                    "
echo "=========================================="
echo "   trust_domain: scotiabank.local"
echo "   svid_ttl:     2 minutes (Renew ~1 min)"
echo "=========================================="
echo "Streaming logs now (Press Ctrl+C to exit)..."
echo ""

cd "$SETUP_DIR" || exit
docker compose logs -f
