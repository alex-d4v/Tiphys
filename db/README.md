# Database Infrastructure (DB)

This directory contains the setup for the project's persistent storage, based on **Neo4j** specifically for handling complex task dependencies and graph relationships.

## Components
- `docker-compose.yml`: Definiton and configuration for the Neo4j container.
- `neo4j.Dockerfile`: Custom Dockerfile for setting up the Neo4j environment with necessary plugins.
- `init.sh`: A shell script to automate the initial environment setup (creating `.env` and data directories).
- `.env`: Environment configuration for ports, authentication, and data paths.

## Setup Instructions
To initialize the database locally, use the provided script:

```bash
./db/init.sh
```

This will:
1. Verify Docker and Docker Compose accessibility.
2. Initialize environment variables in `.env`.
3. Create the data directory for the graph database.
4. Launch the Neo4j container in the background.

## Connection Details
- **Browser Access**: http://localhost:7474
- **Bolt Connection**: bolt://localhost:7687
- **Default Auth**: `neo4j/AstraGenos2026!!` (configured in `.env`)
