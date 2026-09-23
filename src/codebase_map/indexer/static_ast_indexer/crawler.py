# src\codebase_map\indexer\static_ast_indexer\crawler.py
from pathlib import Path
from typing import Iterator, Tuple

def get_python_files(repo_root_path: str) -> Iterator[Tuple[Path, str]]:
    repo_root = Path(repo_root_path).resolve()
    ignore_dirs = {'venv', '.venv', 'env', '.git', '__pycache__', 'node_modules'}

    for py_file in repo_root.rglob('*.py'):
        if any(part in ignore_dirs for part in py_file.parts):
            continue

        relative_path = py_file.relative_to(repo_root)
        parts = list(relative_path.parts)
        parts[-1] = parts[-1].replace('.py', '')
        
        if parts:
            fqn = ".".join(parts)
            yield py_file, fqn