# #!/bin/bash
# set -e

# echo "Waiting for Neo4j to start..."
# until cypher-shell -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" "RETURN 1;" >/dev/null 2>&1; do
#   sleep 2
# done

# echo "Neo4j is up. Running initialization scripts..."

# python /app/run_once.py

# echo "Startup migrations completed."

# # Start the app
# exec "$@"


docker-compose up --build &

sleep 20

python ./run_once.py

# Pull model
echo "Pulling Llama3.1:8b model (this may take a while)..."
docker exec -it ollama ollama pull llama3.1:8b

# Pull model
echo "Pulling nomic-embed-text model (this may take a while)..."
docker exec -it ollama ollama pull nomic-embed-text
