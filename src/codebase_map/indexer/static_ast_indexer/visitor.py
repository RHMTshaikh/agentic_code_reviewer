# src\codebase_map\indexer\static_ast_indexer\visitor.py
import ast
from .resolver import resolve_relative_import

class DefinitionVisitor(ast.NodeVisitor):
    def __init__(self, current_fqn: str, abs_file_path: str, linker, total_lines: int):
        self.current_fqn = current_fqn
        self.file_path = abs_file_path
        self.linker = linker
        
        self.scope_stack = [{"name": "global", "type": "module", "symbols": {}}]
        self.linker.aliases[self.current_fqn] = {}
        self.linker.star_imports[self.current_fqn] = []
        
        if self.current_fqn not in self.linker.definitions:
            self.linker.definitions[self.current_fqn] = {
                "type": "module",
                "name": self.current_fqn.split('.')[-1],
                "file_path": self.file_path,
                "range": [1, total_lines]
            }

    def _get_absolute_path(self, name: str) -> str:
        path_parts = [self.current_fqn]
        for frame in self.scope_stack:
            if frame["name"] != "global":
                path_parts.append(frame["name"])
        if name:
            path_parts.append(name)
        return ".".join(path_parts)

    def _get_current_class_fqn(self) -> str:
        path_parts = [self.current_fqn]
        for frame in self.scope_stack:
            if frame["name"] != "global":
                path_parts.append(frame["name"])
            if frame["type"] == "class":
                return ".".join(path_parts)
        return None

    def _register_symbol(self, name: str, kind: str, fqn: str = None, type_hint: str = None):
        self.scope_stack[-1]["symbols"][name] = {
            "kind": kind,
            "fqn": fqn,
            "type_hint": type_hint
        }

    # FIX: Upgraded to gracefully flatten ast.Call and ast.Subscript
    def _extract_name(self, node) -> str:
        if isinstance(node, ast.Name): 
            return node.id
        elif isinstance(node, ast.Attribute):
            left = self._extract_name(node.value)
            if left: 
                return f"{left}.{node.attr}"
            return node.attr
        elif isinstance(node, ast.Call):
            # Extracts 'super' from 'super().__init__()'
            return self._extract_name(node.func)
        elif isinstance(node, ast.Subscript):
            # Extracts 'List' from 'List[str]'
            return self._extract_name(node.value)
        return None

    def visit_ClassDef(self, node):
        fqn = self._get_absolute_path(node.name)
        parent_fqn = self._get_absolute_path("").rstrip('.')
        
        self._register_symbol(node.name, kind="CLASS", fqn=fqn)
        
        self.linker.definitions[fqn] = {
            "type": "class",
            "name": node.name,
            "file_path": self.file_path,
            "range": [getattr(node, 'lineno', 0), getattr(node, 'end_lineno', 0)],
            "extends": [] 
        }
        
        self.linker.contains_edges.append({
            "type": "contains",
            "source": parent_fqn,
            "target": fqn
        })
        
        for base in node.bases:
            base_name = self._extract_name(base)
            if base_name:
                temp_parent = f"{self.current_fqn}.{base_name}"
                self.linker.unresolved_extends.append((fqn, temp_parent))
        
        self.scope_stack.append({"name": node.name, "type": "class", "symbols": {}})
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node):
        fqn = self._get_absolute_path(node.name)
        parent_fqn = self._get_absolute_path("").rstrip('.')
        
        self._register_symbol(node.name, kind="FUNCTION", fqn=fqn)
        
        parent_type = self.scope_stack[-1]["type"]
        node_type = "class_method" if parent_type == "class" else "function"
        
        self.linker.definitions[fqn] = {
            "type": node_type,
            "name": node.name,
            "file_path": self.file_path,
            "range": [getattr(node, 'lineno', 0), getattr(node, 'end_lineno', 0)]
        }
        
        self.linker.contains_edges.append({
            "type": "contains",
            "source": parent_fqn,
            "target": fqn
        })
        
        self.scope_stack.append({"name": node.name, "type": node_type, "symbols": {}})
        for arg in node.args.args:
            type_hint = self._extract_name(arg.annotation) if arg.annotation else None
            self._register_symbol(arg.arg, kind="ARGUMENT", type_hint=type_hint)
            
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    def visit_Assign(self, node):
        type_hint = self._extract_name(node.annotation) if hasattr(node, 'annotation') and node.annotation else None
        
        # NEW: Capture what the variable is being assigned to (e.g., aliasing a function)
        rhs_name = self._extract_name(node.value) if hasattr(node, 'value') else None

        for target in node.targets if hasattr(node, 'targets') else [node.target]:
            if isinstance(target, ast.Name):
                # NEW: Store the rhs_name as the fqn so we know what this variable points to
                self._register_symbol(target.id, kind="VARIABLE", type_hint=type_hint, fqn=rhs_name)
        self.generic_visit(node)
        
    def visit_AnnAssign(self, node):
        self.visit_Assign(node)

    def visit_Call(self, node):
        call_name = self._extract_name(node.func)
        if call_name:
            parts = call_name.split('.')
            caller_fqn = self._get_absolute_path("").rstrip('.')
            base_name = parts[0]
            
            if base_name == "super":
                self.generic_visit(node)
                return
            
            if base_name in ("self", "cls") and len(parts) == 2:
                class_fqn = self._get_current_class_fqn()
                if class_fqn:
                    temp_target = f"{class_fqn}.{parts[1]}"
                    self.linker.unresolved_calls.append((caller_fqn, temp_target))
                    self.generic_visit(node)
                    return

            resolved_info = None
            for frame in reversed(self.scope_stack):
                if base_name in frame["symbols"]:
                    resolved_info = frame["symbols"][base_name]
                    break

            if resolved_info:
                if resolved_info["kind"] in ("FUNCTION", "CLASS"):
                    base_fqn = resolved_info["fqn"]
                    if len(parts) > 1:
                        temp_target = f"{base_fqn}.{'.'.join(parts[1:])}"
                    else:
                        temp_target = base_fqn
                    self.linker.unresolved_calls.append((caller_fqn, temp_target))
                    
                elif resolved_info["kind"] in ("VARIABLE", "ARGUMENT"):
                    # FIX: If the variable is an alias to a local function (len(parts) == 1)
                    if resolved_info.get("fqn") and len(parts) == 1:
                        temp_target = f"{self.current_fqn}.{resolved_info['fqn']}"
                        self.linker.unresolved_calls.append((caller_fqn, temp_target))
                    # Fallback for typed objects
                    elif resolved_info["type_hint"] and len(parts) > 1:
                        temp_target = f"{self.current_fqn}.{resolved_info['type_hint']}.{'.'.join(parts[1:])}"
                        self.linker.unresolved_calls.append((caller_fqn, temp_target))
            else:
                temp_target = f"{self.current_fqn}.{call_name}"
                self.linker.unresolved_calls.append((caller_fqn, temp_target))
                
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            local_name = alias.asname or alias.name
            self.linker.aliases[self.current_fqn][local_name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        base_fqn = resolve_relative_import(self.current_fqn, node.level, node.module)
        for alias in node.names:
            if alias.name == '*':
                self.linker.star_imports[self.current_fqn].append(base_fqn)
            else:
                local_name = alias.asname or alias.name
                self.linker.aliases[self.current_fqn][local_name] = f"{base_fqn}.{alias.name}"
        self.generic_visit(node)