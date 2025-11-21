import asyncio
from neo4j import GraphDatabase
from typing import Dict, List
from .ast_util import extract_semantics, make_nid, get_text
import ollama
from .neo4j_conn import run
from neo4j_graphrag.embeddings import OllamaEmbeddings

# -----------------------------
# EMBEDDING MODEL
# -----------------------------
embedder = OllamaEmbeddings(model="sellerscrisp/jina-embeddings-v4-text-code-q4")

def embed(text: str) -> List[float]:
    if not text:
        return [0.0] * 2048
    embedding = embedder.embed_query(text)
    return embedding

IMPORTANT_SEM_TYPES = {
    # Core semantic anchors
    "function",
    "class_or_type",

    # Impact analysis essentials
    "call",
    "assignment",
    "variable_declaration",

    # Optional but useful for flow analysis
    "identifier_use",    # keep off unless needed
}

IMPORTANT_NODE_TYPES = {
    # Ensures capturing the “spine” of the AST
    "function_declaration", "function_definition", "method_declaration",
    "class_declaration", "class_definition",
}

def should_embed(node_type: str, sem: Dict):
    st = sem.get("semantic_type")

    # --- 1. semantic-type rule ---
    if st in IMPORTANT_SEM_TYPES:
        return True

    # --- 2. structural anchors ---
    if node_type in IMPORTANT_NODE_TYPES:
        return True

    # --- 3. skip low-value semantic types ---
    # if st in {
    #     "literal",
    #     "identifier_use",
    #     "return_statement",
    #     "control_flow_statement",
    #     "exception_handling",
    #     "import_statement",
    #     None
    # }:
    #     return False

    # default: do not embed
    return False

# -----------------------------
# MAIN UPSERT PIPELINE
# -----------------------------
def upsert_code_graph(repo_name: str, file_path: str, tree, source):
    """
    1. Create repository + file metadata node
    2. Walk AST and collect nodes
    3. Generate embeddings
    4. Build semantic edges
    5. Bulk upsert to Neo4j
    """

    # Nodes & relationships aggregated here
    nodes = []
    rel_child = []
    rel_calls = []
    rel_def = []
    rel_use = []
    rel_repo_file = []
    rel_file_root = []

    root = tree.root_node
    root_id = make_nid(file_path, root)

    # -----------------------------
    # Traverse AST
    # -----------------------------
    def walk(node, parent_id=None):
        nid = make_nid(file_path, node)
        if nid is None:
            return

        text = get_text(node, source)
        sem = extract_semantics(node, source)

        # Embedding input
        emb_text = f"{node.type} | {sem.get('semantic_type')} | {text[:10]}"
        if not should_embed(node.type, sem):
            emb_text = None 

        nodes.append({
            "id": nid,
            "type": node.type,
            "text": text[:250],
            "semantic_type": sem.get("semantic_type"),
            "name": sem.get("name"),
            "file": file_path,
            "repo": repo_name,
            "embedding": embed(emb_text),
        })

        if parent_id:
            rel_child.append({"parent": parent_id, "child": nid})

        # CALL edges
        if sem.get("semantic_type") == "call":
            fn = sem.get("function_name")
            if fn:
                rel_calls.append({"caller": nid, "callee_name": fn})

        # DEF edges
        if sem.get("semantic_type") == "assignment":
            target = sem.get("target_name")
            if target:
                rel_def.append({"node": nid, "var": target})

        # USE edges
        if sem.get("semantic_type") == "identifier_use":
            name = sem.get("name")
            if name:
                rel_use.append({"node": nid, "var": name})

        for c in node.children:
            walk(c, nid)

    # Start traversal
    walk(root)

    # -----------------------------
    # Pre-build repo → file links
    # -----------------------------
    rel_repo_file.append({"repo": repo_name, "file": file_path})

    # File → AST root
    rel_file_root.append({"file": file_path, "root": root_id})

    print(f"Collected {len(nodes)} AST nodes from {file_path} in repo {repo_name}")

    # -----------------------------
    # EXECUTE BULK UPSERTS
    # -----------------------------
    run("""
        MERGE (:Repository {name: $repo})
    """, {"repo": repo_name})

    # 2. Upsert File Node
    run("""
        MERGE (f:File {path: $file, repo: $repo})
        SET f.updatedAt = timestamp()
    """, {"file": file_path, "repo": repo_name})

    # 3. Repo → File edge
    run("""
        MATCH (r:Repository {name: $repo})
        MATCH (f:File {path: $file})
        MERGE (r)-[:HAS_FILE]->(f)
    """, {"repo": repo_name, "file": file_path})

    # 4. Upsert AST nodes
    run("""
        UNWIND $nodes AS n
        MERGE (a:AstNode {id: n.id})
        SET a.type = n.type,
            a.text = n.text,
            a.semantic_type = n.semantic_type,
            a.name = n.name,
            a.file = n.file,
            a.repo = n.repo,
            a.embedding = n.embedding
    """, {"nodes": nodes})

    # 5. File → Root AST
    run("""
        MATCH (f:File {path: $file})
        MATCH (r:AstNode {id: $root})
        MERGE (f)-[:HAS_AST_ROOT]->(r)
    """, {"file": file_path, "root": root_id})

    # 6. AST child edges
    run("""
        UNWIND $rels AS r
        MATCH (p:AstNode {id:r.parent})
        MATCH (c:AstNode {id:r.child})
        MERGE (p)-[:CHILD]->(c)
    """, {"rels": rel_child})

    # 7. CALL edges
    run("""
        UNWIND $calls AS row
        MATCH (caller:AstNode {id: row.caller})
        MATCH (callee:AstNode {name: row.callee_name})
        MERGE (caller)-[:CALLS]->(callee)
    """, {"calls": rel_calls})

    # 8. DEF edges
    run("""
        UNWIND $defs AS row
        MATCH (n:AstNode {id: row.node})
        MERGE (v:Variable {name: row.var})
        MERGE (n)-[:DEF]->(v)
    """, {"defs": rel_def})

    # 9. USE edges
    run("""
        UNWIND $uses AS row
        MATCH (n:AstNode {id: row.node})
        MERGE (v:Variable {name: row.var})
        MERGE (n)-[:USE]->(v)
    """, {"uses": rel_use})

    print(f"✔ AST + Repo/File upsert complete for repo={repo_name}, file={file_path}")
