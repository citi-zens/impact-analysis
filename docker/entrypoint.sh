#!/bin/bash
set -e

echo "Waiting for Neo4j to start..."
until cypher-shell -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" "RETURN 1;" >/dev/null 2>&1; do
  sleep 2
done

echo "Neo4j is up. Running initialization scripts..."

python /app/run_once.py

echo "Startup migrations completed."

# Start the app
exec "$@"
