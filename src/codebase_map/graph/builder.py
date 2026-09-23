# src\codebase_map\graph\builder.py

import sys
from codebase_map.graph.symbol import Symbol
from pathlib import Path
from codebase_map.indexer import scip_index_of_repo, static_ast_index_of_repo
from codebase_map.graph.node import Node



def make_graph_using_scip(project_path: Path):
    # DO NOT process a directory that is a direct python package

    if not project_path.exists():
        print(f"⚠️ The directory '{project_path}' does not exist. Please provide a valid path.")
        sys.exit(1)
        
    import os
    import contextlib

    print("⏳ Indexing codebase...")

    # Send all print statements to the void while this block runs
    # with open(os.devnull, "w", encoding='utf-8') as void, contextlib.redirect_stdout(void):
    clean_json_data = scip_index_of_repo(project_path)

    print("✅ Indexing complete!")
        
    # node's ID will be the fqn
    root_node = Node(name=project_path.name, type='root', fqn='root', abs_path=project_path.as_posix())
    NODES = {root_node.fqn: root_node}
    all_definitions_list: list[Node] = []
    
    # use only to add file nodes
    def add_to_parent(node: Node) -> Node:
        parent_path = Path(node.abs_path).parent
        if parent_path == project_path:
            root_node.add_child(node)
            return 
        
        parent_node = NODES.get(node.parent_fqn())
        if parent_node:
            parent_node.add_child(node)
            return
        parent_node = Node(name=node.parent_name(), fqn=node.parent_fqn(), type='directory', abs_path=parent_path.as_posix())
        NODES[parent_node.fqn] = parent_node
        parent_node.add_child(node)

        add_to_parent(parent_node)
    
    # first add all the module nodes to the NODES
    print("Now adding module nodes...")
    for doc in clean_json_data.get("documents", []):
        rel_path = Path(doc.get("relative_path", ""))
        abs_path = project_path / rel_path
        fqn = rel_path.as_posix().replace('/', '.').rstrip('.py')  # Convert path to scope format
        node = Node(name=rel_path.name, fqn=fqn, type='module', abs_path=abs_path.as_posix())
        NODES[node.fqn] = node
        
        add_to_parent(node)
    
    # then add all the function and class definition nodes to the NODES
    print("Now adding function and class definition nodes...") 
    for doc in clean_json_data.get("documents", []):
        rel_path = Path(doc.get("relative_path", ""))
        file_scope = rel_path.as_posix().replace('/', '.').rstrip('.py')  # Convert path to scope format
        for occ in doc.get("occurrences", []):
            symbol_str = occ.get("symbol", "")
            if not symbol_str or not occ['range']: # Only definitions have a range, so we can skip occurrences without a range
                continue
            
            sym_obj = Symbol(symbol_str)
            if sym_obj.type in ['function', 'class', 'class_method']:
                node = Node(name=sym_obj.name, fqn=f"{file_scope}.{sym_obj.scope}", type=sym_obj.type, range=occ['range'], abs_path=rel_path.as_posix())
                all_definitions_list.append(node)
                NODES[node.fqn] = node

                # find the parent node based on the address
                parent_fqn = node.parent_fqn()
                parent_node = NODES.get(parent_fqn)
                parent_node.add_child(node)

    # then add all the function calls to the NODES
    # find all the definitions in the document first, then find the enclosing function or class for each occurrence
    print("Now adding which functions are being called by which functions...") 
    for caller_node in all_definitions_list:
        start_line, end_line = caller_node.range
        caller_file = Path(caller_node.abs_path)
        for doc in clean_json_data.get("documents", []):
            file = Path(doc['relative_path'])
            if file.resolve() != caller_file.resolve():
                continue

            for occ in doc.get("occurrences", []):
                if occ['symbol_roles'] != 8:  # Role 8 typically indicates a reference/call
                    continue
                refer_line = occ['line']
                if not(start_line <= refer_line <= end_line):
                    continue

                callee_sym = Symbol(occ['symbol'])
                # find this symbol's definition file's relative path in the project
                for doc2 in clean_json_data.get("documents", []):
                    for occ2 in doc2.get("occurrences", []):
                        if occ2['symbol'] == occ['symbol'] and occ2['range']:
                            callee_file = Path(doc2['relative_path'])
                            break
                callee_fqn = f"{callee_file.as_posix().replace('/', '.').rstrip('.py')}.{callee_sym.scope}"
                callee_node = NODES.get(callee_fqn)
                callee_node.called_by.add(caller_node)
                caller_node.calls.add(callee_node)
                    
    return NODES, root_node


def make_graph_using_ast(project_path: Path) -> tuple[dict[str, Node], Node]:
    index_json = static_ast_index_of_repo(project_path)
    
    NODES: dict[str, Node] = {}
    root_node = Node(name=project_path.name, type='root', fqn='root', abs_path=project_path.as_posix())
    NODES[root_node.fqn] = root_node
    
    # Node ID will be the fqn
    
    print(f"Building graph from the data...")
    # use only to add file nodes
    def add_to_parent(node: Node) -> Node:
        
        parent_path = Path(node.abs_path).parent
        if parent_path == project_path:
            root_node.add_child(node)
            return 
        
        parent_node = NODES.get(node.parent_fqn())
        if parent_node:
            parent_node.add_child(node)
            return
        parent_node = Node(name=node.parent_name(), type = 'directory', fqn=node.parent_fqn(), abs_path=parent_path.as_posix())
        NODES[parent_node.fqn] = parent_node
        parent_node.add_child(node)

        add_to_parent(parent_node)
    
    print(f"Adding nodes to the graph...")
    # Create Node instances for each definition
    for fqn, def_info in index_json['nodes'].items():
        node = Node(
            name=def_info['name'],
            type=def_info['type'],
            fqn=fqn,
            range=tuple(def_info['range']) if 'range' in def_info else None,
            abs_path=Path(def_info['file_path']).as_posix(),
        )
        NODES[node.fqn] = node
        
        if node.type == 'module':
            add_to_parent(node)
        

    # Create edges based on the resolved edges
    print("Adding edges to the graph...")
    for edge in index_json['edges']:
        source_fqn = edge['source']
        target_fqn = edge['target']
        
        source_def_info = index_json['nodes'].get(source_fqn)
        target_def_info = index_json['nodes'].get(target_fqn)
        
        if source_def_info and target_def_info:
            source_node = NODES.get(source_fqn)
            target_node = NODES.get(target_fqn)
            
            if source_node and target_node:
                if edge['type'] == 'calls':
                    source_node.add_calls(target_node)
                    target_node.add_called_by(source_node)
                elif edge['type'] == 'contains':
                    source_node.add_child(target_node)
            else:
                raise ValueError(f"Source or target node not found for edge: {edge}")
        else:
            raise ValueError(f"Source or target definition not found for edge: {edge}")
    return NODES, root_node

if __name__ == "__main__":
    from pathlib import Path
    target = r'../document_align'
    target = r'../huggingface_transformer_clone/transformers'
    target = Path(target).absolute().resolve()
    print(target)
    nodes, root_node = make_graph_using_ast(target)
    
    node = nodes.get('src.transformers.core_model_loading.spawn_materialize._job')
    print(node)
    print(len(nodes))
    
    