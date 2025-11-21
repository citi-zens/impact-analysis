from neo4j import GraphDatabase
from neo4j_graphrag.retrievers import HybridRetriever
from neo4j_graphrag.embeddings import OllamaEmbeddings
from typing import Any
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.llm import OllamaLLM
from dotenv import load_dotenv
import os
import subprocess

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME =  os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD =  os.getenv("NEO4J_PASSWORD")

# Connect to the Neo4j database
print("Connecting to Neo4j at:", NEO4J_URI,NEO4J_PASSWORD,NEO4J_USERNAME)
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

embedder = OllamaEmbeddings(
    model="sellerscrisp/jina-embeddings-v4-text-code-q4"
)

retriever = HybridRetriever(
    driver=driver,
    vector_index_name="astVectorIndex",
    fulltext_index_name="astFulltextIndex",
    embedder=embedder,
    return_properties=["id", "semantic_type", "name", "file", "text"]
)
# LLM
llm = OllamaLLM(
    model_name="qwen2.5:1.5b",
)
# Initialize the RAG pipeline
rag = GraphRAG(retriever=retriever, llm=llm)

def get_query_prompt(prompt_type='embed',data:str='',is_fr:bool=True) -> str:
    if prompt_type=='embed':
        query_text = f'''
        You are an impact-analysis engine.

        I will provide you with:
        - A list of AST nodes
        - Their semantic types (function, class, call, assignment, variable_declaration, identifier_use)
        - Child edges (AST structure)
        - CALL edges (caller → callee)
        - DEF/USE edges (for data-flow)
        - File/Module paths for each node

        Your task:
        1. Identify which modules (files or logical components) are MOST impacted by a change.
        2. Impact means:
        - A function calls another function in a different file → propagate impact.
        - A function or class is referenced by another module → impacted.
        - A variable or symbol is defined in one module and used in another → impacted.
        - Parent modules of impacted nodes also receive accumulated impact.

        3. Compute a ranked list where:
        - Higher impact = more references, more calls, more data-flow dependencies.
        - Count both direct and transitive impacts.
        - Group impacts by `repo` and `file`.

        4. Output:
        - A sorted list of modules with:
                module file_path,
                direct_impacts number,
                transitive_impacts number,
                reasons explanations
            

        5. Rules:
        - Treat function and class definitions as the strongest semantic anchors.
        - Treat calls and assignments as primary impact propagation signals.
        - Ignore literal and identifier-only nodes unless they create cross-file references.
        - Propagate impacts along:
                CALLS edges
                DEF → USE edges
                parent-child AST ancestors (but lower weight)
        - Count only meaningful semantic edges.

        Now I will give you the AST nodes and relationships.  
        Analyze them and return the top-impacted modules.
        "{data}"
        '''
    else:
        query_text = f'''
        Given the following AST nodes and their relationships in neo4j, analyze the impact of changes related".

        Use semantic edges like CALLS, DEF/USE, and AST structure to propagate impact.

        Return a ranked list of modules with direct and transitive impact counts and brief reasons for each.

        Feature/Reasoning: here's the data"{data}"
        '''
    return query_text

def run_mcphost(embeddings_output):
    command = [
        os.path.expanduser("~/go/bin/mcphost"),
        "-m", "ollama:qwen2.5:1.5b",
        "--config", os.path.expanduser("~/local.json"),
        "-p", f"analyse impact from neo4j ASTnode based on the based on the modules listed and provide a readme.md as output {embeddings_output}",
        "--quiet"
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise Exception(f"Error executing mcphost: {result.stderr}")

    return result.stdout


def analyze_impact(is_fr:bool=True,data: str='',top_k:int=20):
    response = rag.search(query_text=get_query_prompt(data=data,is_fr=is_fr), retriever_config={"top_k": top_k})
    print(response.answer)
    resp = run_mcphost(get_query_prompt(prompt_type='test',data=response.answer,is_fr=is_fr))
    return resp