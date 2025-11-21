from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME =  os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD =  os.getenv("NEO4J_PASSWORD")

# Connect to the Neo4j database
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

def run(query, params=None):
    with driver.session() as session:
        session.run(query, params or {})