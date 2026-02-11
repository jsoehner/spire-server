#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
import re
import textwrap

# --- Configuration ---
BASE_DIR = os.path.join(os.getcwd(), "spire_setup")
AGENT_SPIFFE_ID = "spiffe://scotiabank.local/my-first-agent"
COMPOSE_FILE = os.path.join(BASE_DIR, "docker-compose.yaml")

def run_cmd(cmd):
    """Runs a shell command and returns output string."""
    try:
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        return result.decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(f"Output: {e.output.decode('utf-8')}")
        sys.exit(1)

def get_container_id(service_name):
    """Dynamically fetches the container ID for a specific service."""
    cmd = f"docker compose -f {COMPOSE_FILE} ps -q {service_name}"
    container_id = run_cmd(cmd)
    if not container_id:
        print(f"Error: Service '{service_name}' is not running.")
        sys.exit(1)
    return container_id

def clean_agent_state():
    """Wipes the agent's local data to prevent 'Unknown Authority' errors."""
    print("--- Cleaning Stale Agent Data ---")
    
    # 1. Stop the agent first
    print("Stopping Agent container...")
    subprocess.run(["docker", "compose", "-f", COMPOSE_FILE, "stop", "spire-agent"], stderr=subprocess.DEVNULL)
    
    # 2. Delete the persistence folder
    agent_data_path = os.path.join(BASE_DIR, "persistence", "agent")
    if os.path.exists(agent_data_path):
        print(f"Removing old agent data: {agent_data_path}")
        try:
            shutil.rmtree(agent_data_path)
        except PermissionError:
            print("Python cannot delete agent data (owned by root). Trying sudo...")
            subprocess.run(f"sudo rm -rf {agent_data_path}", shell=True)
            
    # 3. Re-create the folder with open permissions
    os.makedirs(agent_data_path)
    os.chmod(agent_data_path, 0o777)
    print("Agent state wiped and ready for fresh enrollment.")

def main():
    print(f"--- Adding SPIRE Agent to {BASE_DIR} ---")

    # 1. Clean old data first!
    clean_agent_state()

    # 2. Get Container ID dynamically
    print("Finding SPIRE Server container ID...")
    try:
        server_id = get_container_id("spire-server-1")
    except:
        print("Could not find spire-server-1. Make sure you ran the setup script first.")
        sys.exit(1)

    # 3. Get Trust Bundle
    print("Fetching Trust Bundle...")
    # This fetches the CURRENT server's CA, ensuring they match.
    bundle = run_cmd(f"docker exec {server_id} /opt/spire/bin/spire-server bundle show -format pem")
    
    agent_conf_dir = os.path.join(BASE_DIR, "agent")
    if not os.path.exists(agent_conf_dir):
        os.makedirs(agent_conf_dir)
        os.chmod(agent_conf_dir, 0o777)

    bundle_path = os.path.join(agent_conf_dir, "bootstrap.crt")
    with open(bundle_path, "w") as f:
        f.write(bundle)
    print(f"Saved Trust Bundle to {bundle_path}")

    # 4. Generate Join Token
    print(f"Generating Join Token for {AGENT_SPIFFE_ID}...")
    token_output = run_cmd(f"docker exec {server_id} /opt/spire/bin/spire-server token generate -spiffeID {AGENT_SPIFFE_ID}")
    
    match = re.search(r"Token:\s+([a-f0-9-]+)", token_output)
    if not match:
        print("Failed to parse token from output:", token_output)
        sys.exit(1)
    
    join_token = match.group(1)
    print(f"Token Generated: {join_token}")

    # 5. Create Agent Config
    agent_conf_content = f"""
    agent {{
        data_dir = "/opt/spire/data/agent"
        log_level = "DEBUG"
        server_address = "load-balancer"
        server_port = "8081"
        socket_path = "/tmp/spire-agent/public/api.sock"
        trust_bundle_path = "/opt/spire/conf/agent/bootstrap.crt"
        trust_domain = "scotiabank.local"
        
        join_token = "{join_token}"
    }}

    plugins {{
        NodeAttestor "join_token" {{
            plugin_data {{}}
        }}
        KeyManager "disk" {{
            plugin_data {{
                directory = "/opt/spire/data/agent"
            }}
        }}
        WorkloadAttestor "docker" {{
            plugin_data {{
                use_new_container_locator = true
            }}
        }}
    }}
    """
    
    conf_path = os.path.join(agent_conf_dir, "agent.conf")
    with open(conf_path, "w") as f:
        f.write(textwrap.dedent(agent_conf_content).strip())
    print(f"Created Agent Config at {conf_path}")

    # 6. Append to Docker Compose (Idempotent check)
    with open(COMPOSE_FILE, "r") as f:
        compose_content = f.read()

    if "spire-agent:" not in compose_content:
        print("Appending Agent service to docker-compose.yaml...")
        agent_service = """
  spire-agent:
    image: ghcr.io/spiffe/spire-agent:1.10.1
    restart: always
    depends_on:
      - load-balancer
    volumes:
      - ./agent/agent.conf:/opt/spire/conf/agent/agent.conf
      - ./agent/bootstrap.crt:/opt/spire/conf/agent/bootstrap.crt
      - ./persistence/agent:/opt/spire/data/agent
      - /var/run/docker.sock:/var/run/docker.sock
    command: ["-config", "/opt/spire/conf/agent/agent.conf"]
    pid: "host"
        """
        with open(COMPOSE_FILE, "a") as f:
            f.write(agent_service)
    else:
        print("Agent service already exists in Docker Compose. Skipping append.")

    # 7. Start the Agent
    print("Starting the Agent container...")
    os.chdir(BASE_DIR)
    # --force-recreate ensures we don't reuse the stopped container state
    subprocess.run(["docker", "compose", "up", "-d", "--force-recreate", "spire-agent"])

    print("\n--- Success! ---")
    print("Agent state wiped and process restarted.")
    print("Check logs: docker compose logs -f spire-agent")

if __name__ == "__main__":
    main()
