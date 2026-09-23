# src\codebase_map\gui\streamlit\converter.py
import networkx as nx
from typing import Set, Optional
from codebase_map.graph.node import Node

def build_nx_graph(
    root_node: Node,
    custom_nodes: dict,
    custom_edges: dict,
    search_query: str = "",
    show_containment: bool = True,
    show_calls: bool = True,
    modified_addresses: Optional[Set[str]] = None
) -> nx.DiGraph:
    
    if modified_addresses is None:
        modified_addresses = set()

    G = nx.DiGraph()
    visited: Set[str] = set()

    def traverse(node: Node):
        if not node or getattr(node, "fqn", None) is None or node.fqn in visited:
            return
        visited.add(node.fqn)

        raw_type = getattr(node, "type", "function")
        node_type = str(raw_type).lower().replace("def", "").strip()
        
        props = custom_nodes.get(node_type, custom_nodes.get("module"))
        color = props["color"]
        shape = props["shape"]
        base_size = props["size"]
        font_color = props["font_color"]

        border_width = 1
        border_color = "#1E1E2E"
        if search_query and search_query.lower() in str(node.fqn).lower():
            color = "#F9E2AF"
            border_width = 4
            border_color = "#F38BA8"
            base_size = base_size * 1.5

        raw_name = node.name or ""
        max_display_length = 12
        if len(raw_name) > max_display_length:
            display_label = f"{raw_name[:max_display_length//2]}...{raw_name[-max_display_length//2:]}"
        else:
            display_label = raw_name

        tooltip = (
            f"Name: {raw_name}\n"
            f"FQN: {node.fqn or 'ROOT'}\n"
            f"Type: {node_type}\n"
            f"Calls: {len(getattr(node, 'calls', []))} | Called By: {len(getattr(node, 'called_by', []))}"
        )

        G.add_node(
            node.fqn,
            label=display_label,
            title=tooltip,
            color={"background": color, "border": border_color},
            borderWidth=border_width,
            shape=shape,
            size=base_size,
            base_size=base_size,  # NEW: Inject base size for JavaScript to read
            font={"color": font_color}
        )

        if show_containment:
            c_props = custom_edges["contains"]
            for child in getattr(node, "contains", []):
                if child and getattr(child, "fqn", None) is not None:
                    G.add_edge(
                        node.fqn, child.fqn, 
                        color=c_props["color"], dashes=c_props["dashes"], 
                        width=c_props["width"], 
                        base_width=c_props["width"], # NEW: Injects base size for JS scaling
                        arrows="to",
                        physics=True 
                    )

        if show_calls:
            call_props = custom_edges["calls"]
            for callee in getattr(node, "calls", []):
                callee_addr = callee.fqn if hasattr(callee, "fqn") else str(callee)
                G.add_edge(
                    node.fqn, callee_addr, 
                    color=call_props["color"], dashes=call_props["dashes"], 
                    width=call_props["width"], 
                    base_width=call_props["width"], # NEW: Injects base size for JS scaling
                    arrows="to",
                    physics=True,  
                    length=0       
                )

        for child in getattr(node, "contains", []):
            traverse(child)

    traverse(root_node)
    return G