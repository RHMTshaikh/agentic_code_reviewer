# src\codebase_map\indexer\static_ast_indexer\builder.py
import ast
import json
from .crawler import get_python_files
from .linker import RepositoryLinker
from .visitor import DefinitionVisitor

def index_of_repo(repo_root_path: str):
    linker = RepositoryLinker()
    total_files = sum(1 for _ in get_python_files(repo_root_path))
    processed_files = 0

    for py_file, current_fqn in get_python_files(repo_root_path):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                file_content = f.read()
                
            total_lines = file_content.count('\n') + 1
            tree = ast.parse(file_content, filename=str(py_file))
            
            visitor = DefinitionVisitor(current_fqn, str(py_file), linker, total_lines)
            visitor.visit(tree)
        except SyntaxError:
            pass 
        except Exception as e:
            print(f"Error parsing {py_file}: {e}")
        finally:
            processed_files += 1
            print(f"Progress: {processed_files}/{total_files} files processed", end='\r')
    
    print(" "*200, end='\r')  # Clear the progress line
    print(f"Finished processing {processed_files}/{total_files} files.")
    
    print("Resolving edges...")
    resolved_edges = linker.consolidate()

    return {
        "nodes": linker.definitions,
        "edges": resolved_edges
    }

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    graph_data = index_of_repo(target)
    
    with open("repo_graph.json", "w") as f:
        json.dump(graph_data, f, indent=2)
    print("Graph generated: repo_graph.json")