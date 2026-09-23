import sys
import base64
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

from codebase_map.graph import make_graph_using_ast, make_graph_using_scip
from codebase_map.gui.streamlit.config import NODE_LIMIT, SHAPE_OPTIONS, DEFAULT_NODE_PROPS, DEFAULT_EDGE_PROPS
from codebase_map.gui.streamlit.converter import build_nx_graph
from codebase_map.gui.streamlit.renderer import render_pyvis

st.set_page_config(layout="wide", page_title="Codebase AST & Call Graph Visualizer")

@st.cache_resource
def load_codebase_graph(project_path: Path):
    nodes, root_node = make_graph_using_ast(project_path)
    return nodes, root_node

# --- Sidebar UI ---
with st.sidebar:
    st.header("🔍 Search")
    search_query = st.text_input("Find Node by ID or Name:", placeholder="e.g. main or utils")
    
    st.divider()
    st.header("⚙️ Visual Filters")
    show_calls = st.checkbox("Show Call Graph Edges", value=True)
    show_containment = st.checkbox("Show Directory Containment", value=True)
    enable_physics = st.toggle("Enable Physics Simulation", value=True)
    
    st.divider()
    st.header("🧲 Physics Engine")
    st.caption("Accepts positive/negative decimals. Type 'auto' in Spring Length to scale by node count.")
    phys_gravity = st.text_input("Gravity", value="0")
    phys_central = st.text_input("Central Gravity", value="0.01")
    phys_spring_len = st.text_input("Spring Length", value="auto")
    phys_spring_const = st.text_input("Spring Constant", value="0.1")
    phys_damping = st.text_input("Damping", value="0.4")
    phys_overlap = st.text_input("Avoid Overlap", value="0.1")
    
    st.divider()
    st.header("🎨 Customization")
    
    custom_nodes = {}
    custom_edges = {}
    
    st.subheader("Nodes")
    for node_type, props in DEFAULT_NODE_PROPS.items():
        with st.expander(f"'{node_type.title()}' Nodes"):
            c1, c2 = st.columns(2)
            bg_color = c1.color_picker("Background", props["color"], key=f"c_{node_type}")
            text_color = c2.color_picker("Text Color", props["font_color"], key=f"t_{node_type}")
            shape = st.selectbox("Shape", SHAPE_OPTIONS, index=SHAPE_OPTIONS.index(props["shape"]), key=f"s_{node_type}")
            size = st.slider("Base Size", min_value=5, max_value=50, value=props["size"], key=f"sz_{node_type}")
            custom_nodes[node_type] = {"color": bg_color, "shape": shape, "size": size, "font_color": text_color}

    st.subheader("Edges")
    for edge_type, props in DEFAULT_EDGE_PROPS.items():
        with st.expander(f"'{edge_type.title()}' Edges"):
            e_color = st.color_picker("Edge Color", props["color"], key=f"ec_{edge_type}")
            e_width = st.slider("Thickness", min_value=1, max_value=10, value=props["width"], key=f"ew_{edge_type}")
            e_dashes = st.checkbox("Dashed Line", value=props["dashes"], key=f"ed_{edge_type}")
            custom_edges[edge_type] = {"color": e_color, "width": e_width, "dashes": e_dashes}


# --- Main Execution ---
with st.spinner("Analyzing codebase & rendering geometry..."):
    if len(sys.argv) > 1:
        raw_path = sys.argv[1]
        project_path = Path(raw_path).resolve()
        
        nodes, root_node = load_codebase_graph(project_path)
        print("Building nx graph...")
        nx_graph = build_nx_graph(
            root_node, 
            custom_nodes, 
            custom_edges, 
            search_query, 
            show_containment, 
            show_calls
        )
        
        total_nodes = len(nx_graph.nodes)
        
        def safe_float(val, default):
            try: return float(val)
            except ValueError: return default
            
        # Parse runtime physics settings
        physics_settings = {
            "gravity": safe_float(phys_gravity, 0),
            "centralGravity": safe_float(phys_central, 0.01),
            "springLength": total_nodes // 30 if phys_spring_len.strip().lower() == "auto" else safe_float(phys_spring_len, 100),
            "springConstant": safe_float(phys_spring_const, 0.1),
            "damping": safe_float(phys_damping, 0.4),
            "avoidOverlap": safe_float(phys_overlap, 0.1)
        }
        
        if total_nodes > NODE_LIMIT:
            st.error("🛑 **Graph too large to render!**")
            st.warning(
                f"This repository generated **{total_nodes:,}** nodes. "
                f"The browser canvas cannot handle more than ~{NODE_LIMIT:,} nodes simultaneously without crashing."
            )
            st.info(
                "💡 **How to fix this:**\n"
                "Please choose a smaller repository, or point the tool to a specific **sub-directory** "
                "instead of the entire project root to view a localized graph."
            )
        else:
            st.success(f"Graph generated successfully with {total_nodes} nodes.")
            print("Rendering PyVis HTML...")
            html_data = render_pyvis(
                nx_graph, 
                custom_nodes,
                custom_edges,
                physics=enable_physics,
                physics_params=physics_settings
            )
            b64_html = base64.b64encode(html_data.encode("utf-8")).decode("utf-8")
            iframe_src = f"data:text/html;base64,{b64_html}"
            
            print("Embedding in Streamlit...")
            components.iframe(iframe_src, height=780, scrolling=True)
    else:
        st.error("⚠️ No repository path provided!")
        st.info("Please run the app with a path, e.g.: streamlit run app.py -- ../my_repo")