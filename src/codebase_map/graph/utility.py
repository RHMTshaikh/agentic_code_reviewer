# src\codebase_map\graph\utility.py
from codebase_map.graph.node import Node

def print_tree(node: Node, level=0):
    indent = "  " * level
    print(f"{indent}- {node.type}: {node.fqn}")
    print(f"{indent}  CALLs: {[ child.fqn.split('.')[-1] for child in node.calls]}")
    print(f"{indent}  CALLED BY: {[ '.'.join(parent.fqn.split('.')[-2:]) for parent in node.called_by]}")
    for child in node.contains:
        print_tree(child, level + 1)

def make_tree_string(node: Node, level=0) -> str:
    indent = "  " * level
    tree_str = f"{indent}- {node.type}: {node.fqn}\n"
    tree_str += f"{indent}  CALLs: {[ child.fqn.split('.')[-1] for child in node.calls]}\n"
    tree_str += f"{indent}  CALLED BY: {[ '.'.join(parent.fqn.split('.')[-2:]) for parent in node.called_by]}\n"
    for child in node.contains:
        tree_str += make_tree_string(child, level + 1)
    return tree_str

def get_code_of_node(node: Node) -> str:
    """
    Given a Node object, this function retrieves the corresponding code snippet 
    from the source file with line numbers prefixed.
    """
    if not node.range:
        return "⚠️ No range information available for this node."
    
    start_line, end_line = node.range
    
    # Resolve the file path relative to the repository root
    file_path = node.abs_path

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Adjust for 0-based indexing
    start_line_index = max(0, start_line-1)
    end_line_index = min(len(lines), end_line+1)
    
    # Extract just the lines we need
    extracted_lines = lines[start_line_index:end_line_index]
    
    # Add line numbers (start=start_line_index + 1 makes it 1-indexed for humans)
    numbered_lines = [
        f"{line_num:6} | {line}" 
        for line_num, line in enumerate(extracted_lines, start=start_line_index + 1)
    ]
    
    return ''.join(numbered_lines)
