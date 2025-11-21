from tree_sitter import Language, Parser
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjs
import tree_sitter_typescript as tsts
import tree_sitter_java as tsjava
import tree_sitter_go as tsgo
import tree_sitter_c as tsc
import tree_sitter_cpp as tscpp
import os, json

LANGS = {
    "python": Language(tspython.language()),
    "javascript": Language(tsjs.language()),
    "typescript": Language(tsts.language_typescript()),
    "tsx": Language(tsts.language_tsx()),
    "java": Language(tsjava.language()),
    "go": Language(tsgo.language()),
    "c": Language(tsc.language()),
    "cpp": Language(tscpp.language()),
    "jsx": Language(tsjs.language()),  # same as javascript
}

EXT_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "jsx",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".java": "java",
    ".go": "go",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".h": "c",
    ".hpp": "cpp",
}

parser = Parser()

def detect_lang(path):
    _, ext = os.path.splitext(path)
    return EXT_MAP.get(ext.lower())

def parse_file(file_path: str, language: str = None) -> dict:
    if not os.path.exists(file_path):
        return {"error": "file not found"}

    if language is None:
        language = detect_lang(file_path)
        if language is None:
            return {"error": "unknown file extension"}

    lang_obj = LANGS.get(language)
    if not lang_obj:
        return {"error": f"language not supported: {language}"}

    parser=Parser(lang_obj)
    with open(file_path, "rb") as f:
        code = f.read()

    tree = parser.parse(code)
    return tree, code
