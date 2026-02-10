#!/usr/bin/env python3
import os
import shutil
import subprocess
import textwrap
import sys
import time

# --- Configuration ---
PROJECT_NAME = "spire-ha-demo"
TRUST_DOMAIN = "scotiabank.local"
DB_USER = "spire"
DB_PASS = "spire-secret"
DB_NAME = "spire"
BASE_DIR = os.path.join(os.getcwd(), "spire_setup")

def write_file(path, content, mode=0o644):
    dir_name = os.path.dirname(path)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    with open(path, "w") as f:
        f.write(textwrap.dedent(content).strip())
    os.chmod(path, mode)
    print(f"Updated: {path}")

def prepare_directories():
    print("--- Preparing Directories ---")
    dirs = [
        f"{BASE_DIR}/persistence/db",
        f"{BASE_DIR}/persistence/server1",
        f"{BASE_DIR}/persistence/server2",
    ]
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d)
        os.chmod(d, 0o777)

def generate_configs():
    print(f"--- Generating High-Frequency Renewal Configs in {BASE_DIR} ---")
    
    prepare_directories()

    # 1. Postgres Initialization
    # Note: We use raw string r"" to fix the invalid escape sequence warning
    write_file(f"{BASE_DIR}/db-init/init.sql", rf"""
        CREATE USER {DB_USER} WITH PASSWORD '{DB_PASS}';
        CREATE DATABASE {DB_NAME} OWNER {DB_USER};
        \c {DB_NAME};
        GRANT ALL ON SCHEMA public TO {DB_USER};
    """)

    # 2. SPIRE Server Config
    # TTL = 2m forces renewal at 1m (50% mark)
    server_conf_template = """
        server {{
            bind_address = "0.0.0.0"
            bind_port = "8081"
            socket_path = "/tmp/spire-server/private/api.sock"
            trust_domain = "{trust_domain}"
            data_dir = "/opt/spire/data/server"
            log_level = "DEBUG"
            
            default_x509_svid_ttl = "2m"
            
            ca_subject = {{
                country = ["CA"]
                organization = ["Scotiabank"]
            }}
        }}

        plugins {{
            DataStore "sql" {{
                plugin_data {{
                    database_type = "postgres"
                    connection_string = "host=postgres user={db_user} password={db_pass} dbname={db_name} sslmode=disable"
                }}
            }}
            KeyManager "disk" {{
                plugin_data {{
                    keys_path = "/opt/spire/data/server/keys.json"
                }}
            }}
            NodeAttestor "join_token" {{
                plugin_data {{}}
            }}
        }}
    """
    
    formatted_conf = server_conf_template.format(
        trust_domain=TRUST_DOMAIN, db_user=DB_USER, db_pass=DB_PASS, db_name=DB_NAME
    )

    write_file(f"{BASE_DIR}/server1/server.conf", formatted_conf)
    write_file(f"{BASE_DIR}/server2/server.conf", formatted_conf)

    # 3. NGINX Load Balancer Config
    nginx_conf = f"""
        worker_processes 1;
        events {{ worker_connections 1024; }}

        stream {{
            upstream spire_servers_tcp {{
                server spire-server-1:8081;
                server spire-server-2:8081;
            }}
            server {{
                listen 8081;
                proxy_pass spire_servers_tcp;
            }}
        }}

        http {{
            upstream spire_servers_grpc {{
                server spire-server-1:8081;
                server spire-server-2:8081;
            }}
            server {{
                listen 80 http2;
                server_name {TRUST_DOMAIN} spire.{TRUST_DOMAIN};

                location /registration {{
                    grpc_pass grpc://spire_servers_grpc;
                    grpc_set_header Host spire-server-1;
                }}
                
                location / {{
                    grpc_pass grpc://spire_servers_grpc;
                }}
            }}
        }}
    """
    write_file(f"{BASE_DIR}/nginx/nginx.conf", nginx_conf)

    # 4. Docker Compose
    docker_compose = f"""
        services:
          postgres:
            image: postgres:15
            restart: always
            environment:
              POSTGRES_PASSWORD: admin-password
            volumes:
              - ./db-init:/docker-entrypoint-initdb.d
              - ./persistence/db:/var/lib/postgresql/data
            healthcheck:
              test: ["CMD-SHELL", "pg_isready -U postgres"]
              interval: 5s
              timeout: 5s
              retries: 5

          spire-server-1:
            image: ghcr.io/spiffe/spire-server:1.10.1
            restart: always
            command: ["-config", "/opt/spire/conf/server/server.conf"]
            depends_on:
              - postgres
            volumes:
              - ./server1/server.conf:/opt/spire/conf/server/server.conf
              - ./persistence/server1:/opt/spire/data/server
            
          spire-server-2:
            image: ghcr.io/spiffe/spire-server:1.10.1
            restart: always
            command: ["-config", "/opt/spire/conf/server/server.conf"]
            depends_on:
              - postgres
            volumes:
              - ./server2/server.conf:/opt/spire/conf/server/server.conf
              - ./persistence/server2:/opt/spire/data/server

          load-balancer:
            image: nginx:latest
            restart: always
            ports:
              - "80:80"     # HTTP/2 Entry
              - "8081:8081" # Direct TCP Entry
            volumes:
              - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
            depends_on:
              - spire-server-1
              - spire-server-2
    """
    write_file(f"{BASE_DIR}/docker-compose.yaml", docker_compose)

def launch_stack():
    print("\n--- Launching Infrastructure ---")
    os.chdir(BASE_DIR)
    
    # 1. Stop existing (clean slate)
    print("Stopping any existing containers...")
    subprocess.run(["docker", "compose", "down"], stderr=subprocess.DEVNULL)
    
    # 2. Start fresh
    print("Starting containers (postgres, servers, load-balancer)...")
    subprocess.run(["docker", "compose", "up", "-d"])
    
    print("\n✅ Stack launched successfully.")

if __name__ == "__main__":
    generate_configs()
    launch_stack()
