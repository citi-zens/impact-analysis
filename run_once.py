from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME =  os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD =  os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

def run(query, params=None):
    with driver.session() as session:
        session.run(query, params or {})

def create_vector_indexes():
    run("""
        CREATE VECTOR INDEX astVectorIndex IF NOT EXISTS
        FOR (n:AstNode) ON (n.embedding)
        OPTIONS {
        indexConfig: {
            `vector.dimensions`: 2048,
            `vector.similarity_function`: "cosine"
        }
        };
    """)
    # Fulltext index
    run("""
        CREATE FULLTEXT INDEX astFulltextIndex IF NOT EXISTS
        FOR (n:AstNode) ON EACH [n.text, n.name, n.semantic_type]
    """)
    print("✔ Vector + fulltext indexes ready.")

create_vector_indexes()