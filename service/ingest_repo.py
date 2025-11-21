from .utils.repo_utils import clone_repo, list_source_files
from .parser.ts_parser import parse_file
from .graph.ast_with_embeddings import upsert_code_graph
from dotenv import load_dotenv
import os   
load_dotenv()

LOCAL_PATH=os.getenv("LOCAL_REPO_PATH")


def initiate_graph(REPO_NAME:str):
    files = list_source_files(LOCAL_PATH)
    print(files)
    for f in files:
        print("Parsing", f)
        tree, code = parse_file(f)
        upsert_code_graph(REPO_NAME, f, tree, code)

    print("AST ingestion completed.")