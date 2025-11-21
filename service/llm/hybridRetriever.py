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
    # model="sellerscrisp/jina-embeddings-v4-text-code-q4"
    model="nomic-embed-text"
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
    model_name="llama3.1:8b",
)
# Initialize the RAG pipeline
rag = GraphRAG(retriever=retriever, llm=llm)

def get_query_prompt(prompt_type='embed',data:str='',is_fr:bool=True) -> str:
    if prompt_type=='embed':
        query_text = f'''
        You are an expert software-impact analyzer. 
        You have access to the entire AST of the codebase stored in Neo4j, 
        which will be retrieved through a hybrid retriever (vector + keyword). 

        Your task
        Given the following input data, which may be a Feature Request (FR) or Pull Request (PR),
        identify ALL modules, services, files, classes, functions, and dependency chains 
        that are likely to be impacted — directly, indirectly, or through semantic coupling.

        Use the complete impact taxonomy below to reason
        - Direct Code Impacts
        - Dependency & Integration Impacts
        - Behavioral & Logical Impacts
        - Data & Persistence Impacts
        - Interface & Contract Impacts
        - Non-Functional Impacts
        - Testing & Quality Impacts
        - Infrastructure & Deployment Impacts
        - Hidden Semantic Impacts
        - Human & Process Impacts

        Output Format (STRICT)
        
        primary_entities - [ ... ],     // directly mentioned or modified items
        structural_impacts - [ ... ],   // imports, inheritance, module-level links
        dependency_impacts - [ ... ],   // upstream/downstream microservices, events, DB
        behavioral_impacts - [ ... ],   // logic, state, business rules
        interface_impacts -[ ... ],    // API, message, schema drifts
        hidden_impacts - [ ... ],       // reflection, feature flags, AOP, runtime coupling
        test_impacts - [ ... ],         // unit/integration fixtures or unused paths
        infra_impacts - [ ... ],        // CI/CD, env vars, config drift
        output_references - [ ... ]     // ONLY Neo4j node labels/keys to query later
        

        Where
        - Each list must contain references in the format understood by the graph 
        (e.g. ModuleName, ClassName, FunctionName, FilePath, ServiceName)
        - Do NOT write any Cypher queries here.
        - Do NOT summarize the PR/FR.
        - Only extract IMPACTS and affected graph entities.

        Now analyze the following input


        "{data}"
        '''
    else:
        query_text = f'''
        You are an expert Neo4j Cypher generation agent.

        You receive JSON input in the exact structure:
        
        "primary_entities": [...],
        "structural_impacts": [...],
        "dependency_impacts": [...],
        "behavioral_impacts": [...],
        "interface_impacts": [...],
        "hidden_impacts": [...],
        "test_impacts": [...],
        "infra_impacts": [...],
        "output_references": [...]
        

        Your job:
        Generate Cypher queries that will:
        1. Fetch all AST nodes associated with these entities
        2. Traverse imports, calls, inheritance, and dependency edges
        3. Identify transitive impacts (depth 1–5)
        4. Detect upstream/downstream modules
        5. Identify event/message/API consumers
        6. Resolve hidden/semantic couplings
        7. Collect all affected nodes, files, modules, and services

        RULES:
        - For every entity, produce at least one Cypher MATCH query.
        - Use labels like :Module, :Class, :Function, :File, :Service, :Event, :Api, :Config 
        only if they exist in the graph (infer from names).
        - Use parameterized Cypher where possible.
        - Combine related queries using CALL  to avoid duplication.
        - ALWAYS return:
        moduleName, filePath, className, functionName, serviceName, reasonForImpact
        - Do NOT produce explanations or English text. 
        - Output only Cypher queries or CALL blocks.

        Input to analyze:
        {data}

        '''
    import re

    def sanitize_query(q: str) -> str:
        if not q or not isinstance(q, str):
            return ""

        # Remove Lucene special characters
        cleaned = re.sub(r'[+\-\!\(\)\{\}\[\]\^"~\*\?:\\\/]', ' ', q)

        # Collapse multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)

        return cleaned.strip()

    
    return sanitize_query(query_text)


def run_mcphost(embeddings_output):
    command = [
        os.path.expanduser("~/go/bin/mcphost"),
        "-m", "ollama:llama3.1:8b",
        "--config", os.path.expanduser("./local.json"),
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

def analyze_impact(is_fr:bool=True,data: str='',top_k:int=300):
    response = rag.search(query_text=get_query_prompt(data=data,is_fr=is_fr), retriever_config={"top_k": top_k})
    print(response.answer)
    resp = run_mcphost(get_query_prompt(prompt_type='test',data=response.answer,is_fr=is_fr))
    
    return resp

