# src\codebase_map\gui\streamlit\config.py

import math

NODE_LIMIT = 2000

SHAPE_OPTIONS = ["box", "dot", "diamond", "square", "triangle", "star"]

DEFAULT_NODE_PROPS = {
    "root": {"color": "#CDD6F4", "shape": "dot", "size": 30, "font_color": "#FFFFFF"},  
    "directory": {"color": "#F6EA07", "shape": "box", "size": 20, "font_color": "#676867"},       
    "module": {"color": "#90EE90", "shape": "box", "size": 20, "font_color": "#11111B"},          
    "class": {"color": "#FF0000", "shape": "dot", "size": 18, "font_color": "#CDD6F4"},       
    "function": {"color": "#4169E1", "shape": "dot", "size": 12, "font_color": "#CDD6F4"},    
    "class_method": {"color": "#F97979", "shape": "dot", "size": 12, "font_color": "#CDD6F4"},
}

DEFAULT_EDGE_PROPS = {
    "calls": {"color": "#ADD8E6", "dashes": True, "width": 1},
    "contains": {"color": "#ADD8E6", "dashes": False, "width": 1},
}