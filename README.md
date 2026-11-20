You *may* have to delete the files in the persistence/db/* to get this to work!

(spire2) ➜  spire-server git:(main) ✗ ./run.sh                
==========================================
   🚀 Starting SPIRE HA Demo Automation   
==========================================
Step 1: Running Infrastructure Setup (setup_demo_v9.py)...
--- Generating High-Frequency Renewal Configs in /Users/jsoehner/spire-server/spire_setup ---
--- Preparing Directories ---
Updated: /Users/jsoehner/spire-server/spire_setup/db-init/init.sql
Updated: /Users/jsoehner/spire-server/spire_setup/server1/server.conf
Updated: /Users/jsoehner/spire-server/spire_setup/server2/server.conf
Updated: /Users/jsoehner/spire-server/spire_setup/nginx/nginx.conf
Updated: /Users/jsoehner/spire-server/spire_setup/docker-compose.yaml

--- Launching Infrastructure ---
Stopping any existing containers...
Starting containers (postgres, servers, load-balancer)...
[+] up 5/5
 ✔ Network spire_setup_default            Created                                                                                                                                                                                             0.0s
 ✔ Container spire_setup-postgres-1       Created                                                                                                                                                                                             0.0s
 ✔ Container spire_setup-spire-server-1-1 Created                                                                                                                                                                                             0.0s
 ✔ Container spire_setup-spire-server-2-1 Created                                                                                                                                                                                             0.0s
 ✔ Container spire_setup-load-balancer-1  Created                                                                                                                                                                                             0.0s

✅ Stack launched successfully.
✅ Infrastructure setup complete.
⏳ Waiting 15 seconds for Postgres and SPIRE Server to stabilize...
Step 2: Registering Agent (add_agent-v3.py)...
--- Adding SPIRE Agent to /Users/jsoehner/spire-server/spire_setup ---
Finding SPIRE Server container ID...
Found Server ID: 1a849a52916d57ad8994bc2541fa2ec2b3e7aad11c7dc85bda6afb619c53a4e9
Fetching Trust Bundle...
Saved Trust Bundle to /Users/jsoehner/spire-server/spire_setup/agent/bootstrap.crt
Generating Join Token for spiffe://scotiabank.local/my-first-agent...
Token Generated: 0a8f541e-5bf2-41fb-a231-5f631946b740
Created Agent Config at /Users/jsoehner/spire-server/spire_setup/agent/agent.conf
Appending Agent service to docker-compose.yaml...
Restarting the Agent container...
[+] up 6/6
 ✔ Image ghcr.io/spiffe/spire-agent:1.10.1 Pulled                                                                                                                                                                                             1.6s
 ✔ Container spire_setup-postgres-1        Running                                                                                                                                                                                            0.0s
 ✔ Container spire_setup-spire-server-2-1  Running                                                                                                                                                                                            0.0s
 ✔ Container spire_setup-spire-server-1-1  Running                                                                                                                                                                                            0.0s
 ✔ Container spire_setup-load-balancer-1   Running                                                                                                                                                                                            0.0s
 ✔ Container spire_setup-spire-agent-1     Created                                                                                                                                                                                            0.0s

--- Success! ---
Agent config updated and container restarted.
Check logs: docker compose logs -f spire-agent
✅ Agent registered and started.
==========================================
   🎉 Demo is Running!                    
==========================================
   trust_domain: scotiabank.local
   svid_ttl:     2 minutes (Renew ~1 min)
==========================================
Streaming logs now (Press Ctrl+C to exit)...

To stop the container, change to the spire_setup directory and issue docker compose down.
(spire2) ➜  spire-server git:(main) ✗ cd spire_setup 
(spire2) ➜  spire_setup git:(main) ✗ docker compose down                                                                   
[+] down 6/6
 ✔ Container spire_setup-spire-agent-1    Removed                                                                                                                                                                                             0.1s
 ✔ Container spire_setup-load-balancer-1  Removed                                                                                                                                                                                             0.2s
 ✔ Container spire_setup-spire-server-1-1 Removed                                                                                                                                                                                             0.1s
 ✔ Container spire_setup-spire-server-2-1 Removed                                                                                                                                                                                             0.2s
 ✔ Container spire_setup-postgres-1       Removed                                                                                                                                                                                             0.1s
 ✔ Network spire_setup_default            Removed

---

## 🔐 SBOM, CBOM & PQC Governance

This repository integrates the [`jsoehner/jsi-bom-actions`](https://github.com/jsoehner/jsi-bom-actions) GitHub Action ([`.github/workflows/sbom-cbom.yml`](.github/workflows/sbom-cbom.yml)) for automated Software Bill of Materials (SBOM), Cryptographic Bill of Materials (CBOM), and Post-Quantum Cryptography (PQC) readiness auditing.

- **Latest Audit Report:** [`docs/security/CRYPTOGRAPHIC_AUDIT.md`](docs/security/CRYPTOGRAPHIC_AUDIT.md)
- **Learn More:** [jsoehner/jsi-bom-actions](https://github.com/jsoehner/jsi-bom-actions)

---

## Architectural Decision Records (ADRs)

Key architectural decisions governing this repository's security, supply chain, and cryptography strategy are documented under [`docs/adr/`](docs/adr/):

- [**ADR-0001: Automated SBOM and CBOM Supply Chain Governance Pipeline**](docs/adr/0001-automated-sbom-cbom-supply-chain-governance.md) - Context, alternatives considered, decision rationale, and downstream consequences for adopting automated dual-engine SBOM/CBOM scanning, AST call-site analysis, and CI gate verification.
