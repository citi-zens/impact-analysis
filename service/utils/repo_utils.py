import os
import subprocess

SOURCE_EXT = [".java", ".js", ".ts", ".py", ".go", ".kt"]

def clone_repo(url, path):
    if not os.path.exists(path):
        subprocess.run(["git", "clone", url, path])

def list_source_files(root):
    paths = []
    for d, _, files in os.walk(root):
        for f in files:
            if any(f.endswith(ext) for ext in SOURCE_EXT):
                paths.append(os.path.join(d, f))
    return paths