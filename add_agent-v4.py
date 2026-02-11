#!/usr/bin/env python3
import os
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

def main():
    print(f"--- Adding SPIRE Agent to {BASE_DIR} ---")

    # 1. Get Container ID dynamically
    print("Finding SPIRE Server container ID...")
    try:
        server_id = get_container_id("spire-server-1")
        print(f"Found Server ID: {server_id}")
    except:
        print("Could not find spire-server-1. Make sure you ran the setup script first.")
        sys.exit(1)

    # 2. Get Trust Bundle
    print("Fetching Trust Bundle...")
    bundle = run_cmd(f"docker exec {server_id} /opt/spire/bin/spire-server bundle show -format pem")
    
    agent_conf_dir = os.path.join(BASE_DIR, "agent")
    if not os.path.exists(agent_conf_dir):
        os.makedirs(agent_conf_dir)
        os.chmod(agent_conf_dir, 0o777)

    bundle_path = os.path.join(agent_conf_dir, "bootstrap.crt")
    with open(bundle_path, "w") as f:
        f.write(bundle)
    print(f"Saved Trust Bundle to {bundle_path}")

    # 3. Generate Join Token
    print(f"Generating Join Token for {AGENT_SPIFFE_ID}...")
    token_output = run_cmd(f"docker exec {server_id} /opt/spire/bin/spire-server token generate -spiffeID {AGENT_SPIFFE_ID}")
    
    match = re.search(r"Token:\s+([a-f0-9-]+)", token_output)
    if not match:
        print("Failed to parse token from output:", token_output)
        sys.exit(1)
    
    join_token = match.group(1)
    print(f"Token Generated: {join_token}")

    # 4. Create Agent Config
    # FIX: Added 'use_new_container_locator = true' to WorkloadAttestor
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
                # This fixes the warning log
                use_new_container_locator = true
            }}
        }}
    }}
    """
    
    conf_path = os.path.join(agent_conf_dir, "agent.conf")
    with open(conf_path, "w") as f:
        f.write(textwrap.dedent(agent_conf_content).strip())
    print(f"Created Agent Config at {conf_path}")

    # 5. Prepare Persistence for Agent
    agent_data_dir = os.path.join(BASE_DIR, "persistence", "agent")
    if not os.path.exists(agent_data_dir):
        os.makedirs(agent_data_dir)
    os.chmod(agent_data_dir, 0o777)

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
    print("Restarting the Agent container...")
    os.chdir(BASE_DIR)
    # We force recreate to ensure the new config is picked up if the volume mount cached it
    subprocess.run(["docker", "compose", "up", "-d", "--force-recreate", "spire-agent"])

    print("\n--- Success! ---")
    print("Agent updated to use new container locator.")
    print("Check logs: docker compose logs -f spire-agent")

if __name__ == "__main__":
    main()
