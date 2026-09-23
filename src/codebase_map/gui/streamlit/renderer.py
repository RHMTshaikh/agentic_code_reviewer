import json
import networkx as nx
from pyvis.network import Network

def render_pyvis(graph: nx.DiGraph, custom_nodes: dict, custom_edges: dict, physics: bool = True, physics_params: dict = None) -> str:
    net = Network(
        height="750px", 
        width="100%", 
        bgcolor="#1E1E2E", 
        directed=True,
        cdn_resources="in_line" 
    )
    net.from_nx(graph)

    vis_options = {
        "layout": {"randomSeed": 42},
        "interaction": {"zoomSpeed": 0.3, "navigationButtons": True},
        "nodes": { "font": { "size": 14 } },
        "edges": {
            "smooth": {"type": "continuous"},
            "font": { "size": 14 },
            "arrows": {"to": {"scaleFactor": 0.5}}
        }
    }
    
    number_of_nodes = len(graph.nodes)
    
    if physics:
        vis_options["physics"] = {
            "forceAtlas2Based": physics_params,
            "solver": "forceAtlas2Based",
            "stabilization": {
                "enabled": True,
                "iterations": number_of_nodes * 2,
                "updateInterval": 25,
                "fit": True
            }
        }
    else:
        vis_options["physics"] = {"enabled": False}

    net.set_options(json.dumps(vis_options))
    html_data = net.generate_html()

    js_zoom_logic = """
        network.on("zoom", function (params) {
            var scale = network.getScale(); 
            var targetFontSize = 14;
            var maxFontSize = 20;       
            
            var zoomThreshold = maxFontSize / targetFontSize;
            
            var newFontSize = targetFontSize;
            var edgeScaleRatio = 1.0;
            var baseArrowScale = 0.5;  // Default normal size
            var newArrowScale = baseArrowScale;
            
            if (scale > zoomThreshold) {
                newFontSize = maxFontSize / scale;
                edgeScaleRatio = zoomThreshold / scale;
                newArrowScale = baseArrowScale * edgeScaleRatio;
            }
            
            network.setOptions({
                nodes: { font: { size: newFontSize } },
                edges: { 
                    font: { size: newFontSize },
                    arrows: { to: { scaleFactor: newArrowScale } }
                }
            });
            
            requestAnimationFrame(function() {
                var edgesData = network.body.data.edges;
                var allEdges = edgesData.get();
                var edgeUpdates = [];

                for (var i = 0; i < allEdges.length; i++) {
                    var edge = allEdges[i];
                    if (edge.base_width !== undefined) {
                        var newWidth = edge.base_width * edgeScaleRatio;
                        newWidth = Math.max(newWidth, 0.1); 
                        newWidth = Math.round(newWidth * 100) / 100;
                        var currentWidth = Math.round(edge.width * 100) / 100;

                        if (currentWidth !== newWidth) {
                            edgeUpdates.push({ id: edge.id, width: newWidth });
                        }
                    }
                }
                if (edgeUpdates.length > 0) edgesData.update(edgeUpdates);
                
                var nodesData = network.body.data.nodes;
                var allNodes = nodesData.get();
                var nodeUpdates = [];
                
                for (var j = 0; j < allNodes.length; j++) {
                    var node = allNodes[j];
                    if (node.base_size !== undefined) {
                        var newSize = node.base_size * edgeScaleRatio;
                        newSize = Math.max(newSize, 1); 
                        newSize = Math.round(newSize * 100) / 100;
                        var currentSize = Math.round(node.size * 100) / 100;
                        
                        if (currentSize !== newSize) {
                            nodeUpdates.push({ id: node.id, size: newSize });
                        }
                    }
                }
                if (nodeUpdates.length > 0) nodesData.update(nodeUpdates);
            });
        });

        network.emit("zoom", {scale: network.getScale()});
        
        return network;
    """
    
    html_data = html_data.replace("return network;", js_zoom_logic)

    legend_html = """
    <div style="position: absolute; top: 15px; right: 20px; z-index: 1000; background: rgba(30,30,46,0.85); 
                padding: 15px; border: 1px solid #585B70; border-radius: 8px; color: #CDD6F4; font-family: sans-serif; min-width: 150px;">
        <b style="font-size: 15px; display: block; border-bottom: 1px solid #585B70; padding-bottom: 5px; margin-bottom: 10px;">Legend</b>
        <b style="font-size: 12px; color: #A6ADC8; text-transform: uppercase;">Nodes</b><br>
    """
    
    for node_type, props in custom_nodes.items():
        css_shape = "border-radius: 50%;" if props["shape"] in ["dot", "circle", "ellipse"] else "border-radius: 2px;"
        legend_html += f"""
        <div style="display: flex; align-items: center; margin-top: 6px;">
            <div style="width: 14px; height: 14px; background-color: {props['color']}; {css_shape} margin-right: 10px; border: 1px solid #1E1E2E;"></div>
            <span style="font-size: 13px;">{node_type.title()}</span>
        </div>
        """
        
    legend_html += """<br><b style="font-size: 12px; color: #A6ADC8; text-transform: uppercase;">Edges</b><br>"""
    
    for edge_type, props in custom_edges.items():
        border_style = "dashed" if props["dashes"] else "solid"
        display_width = min(props["width"], 4)
        legend_html += f"""
        <div style="display: flex; align-items: center; margin-top: 6px;">
            <div style="width: 22px; border-bottom: {display_width}px {border_style} {props['color']}; margin-right: 10px; display: flex; justify-content: flex-end; align-items: center;">
                <span style="color: {props['color']}; font-weight: bold; margin-right: -5px;">&#10148;</span>
            </div>
            <span style="font-size: 13px;">{edge_type.title()}</span>
        </div>
        """

    legend_html += "</div>"
    html_data = html_data.replace("<body>", f"<body>\n{legend_html}")
    
    return html_data