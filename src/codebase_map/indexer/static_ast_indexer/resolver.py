# src\codebase_map\indexer\static_ast_indexer\resolver.py
def resolve_relative_import(current_fqn: str, level: int, imported_module: str = None) -> str:
    if level == 0:
        return imported_module if imported_module else ""

    parts = current_fqn.split('.')
    parts = parts[:-1]
        
    if level > 1:
        drop_count = level - 1
        if drop_count > len(parts):
            return "" 
        parts = parts[:-drop_count]
        
    if imported_module:
        parts.append(imported_module)
        
    return ".".join(parts)