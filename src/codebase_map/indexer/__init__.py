# src\codebase_map\indexer\__init__.py
from .scip_indexer import index_of_repo as scip_index_of_repo
from .static_ast_indexer import index_of_repo as static_ast_index_of_repo

__all__ = ["scip_index_of_repo", "static_ast_index_of_repo"]