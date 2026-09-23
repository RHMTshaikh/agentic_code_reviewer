# src\codebase_map\indexer\static_ast_indexer\linker.py
import time
import sys

class RepositoryLinker:
    def __init__(self):
        self.definitions = {}          
        self.aliases = {}              
        self.star_imports = {}         
        
        self.contains_edges = []       
        self.unresolved_calls = []     
        self.unresolved_extends = []   
        
        self._resolution_cache = {}
        self.hits = 0
        self.misses = 0

    def resolve_target(self, temporary_id: str, visited: set = None, depth: int = 0) -> str:
        if visited is None:
            visited = set()
            
        # 1. INFINITE LOOP FAILSAFE: Force-break deep cyclic structures
        if depth > 100:
            return "ERROR_MAX_DEPTH"

        if temporary_id in self._resolution_cache:
            self.hits += 1
            return self._resolution_cache[temporary_id]
            
        if temporary_id in visited:
            return "ERROR_CIRCULAR_IMPORT"

        self.misses += 1
        
        # Add to visited BEFORE processing
        visited.add(temporary_id)
        
        result = self._resolve_target_core(temporary_id, visited, depth + 1)
        
        # Remove from visited AFTER processing (Optimized DFS logic)
        visited.remove(temporary_id)
        
        self._resolution_cache[temporary_id] = result
        return result

    def _resolve_target_core(self, temporary_id: str, visited: set, depth: int) -> str:
        if temporary_id in self.definitions:
            return temporary_id
            
        parts = temporary_id.rsplit('.', 1)
        if len(parts) < 2:
            return f"EXTERNAL:{temporary_id}"
            
        module_fqn, symbol = parts
        
        init_id = f"{module_fqn}.__init__.{symbol}"
        if init_id in self.definitions:
            return init_id

        if module_fqn in self.aliases and symbol in self.aliases[module_fqn]:
            return self.resolve_target(self.aliases[module_fqn][symbol], visited, depth)
            
        init_fqn = f"{module_fqn}.__init__"
        if init_fqn in self.aliases and symbol in self.aliases[init_fqn]:
            return self.resolve_target(self.aliases[init_fqn][symbol], visited, depth)

        for fqn_to_check in [module_fqn, init_fqn]:
            if fqn_to_check in self.star_imports and not symbol.startswith('_'):
                for star_module in reversed(self.star_imports[fqn_to_check]):
                    guessed = f"{star_module}.{symbol}"
                    result = self.resolve_target(guessed, visited, depth)
                    if not result.startswith("ERROR") and not result.startswith("EXTERNAL"):
                        return result

        parent_resolved = self.resolve_target(module_fqn, visited, depth)
        if not parent_resolved.startswith("ERROR") and not parent_resolved.startswith("EXTERNAL"):
            combined_fqn = f"{parent_resolved}.{symbol}"
            
            if combined_fqn in self.definitions:
                return combined_fqn
                
            if parent_resolved in self.definitions and self.definitions[parent_resolved].get("type") == "class":
                extends_list = self.definitions[parent_resolved].get("extends", [])
                for parent_fqn in extends_list:
                    inherited_target = f"{parent_fqn}.{symbol}"
                    inherited_resolved = self.resolve_target(inherited_target, visited, depth)
                    if not inherited_resolved.startswith("ERROR") and not inherited_resolved.startswith("EXTERNAL"):
                        return inherited_resolved

        return f"EXTERNAL_OR_UNRESOLVED:{temporary_id}"

    def consolidate(self):
        self.hits = 0
        self.misses = 0

        print(f"Resolving inheritance for {len(self.unresolved_extends)} classes...")
        for class_fqn, temp_parent in self.unresolved_extends:
            true_parent = self.resolve_target(temp_parent)
            if not true_parent.startswith("EXTERNAL") and not true_parent.startswith("ERROR"):
                self.definitions[class_fqn]["extends"].append(true_parent)
                
        print("Cleaning up method calls...")
        for fqn, node_data in self.definitions.items():
            if node_data.get("type") == "class":
                if "extends" in node_data and not node_data["extends"]:
                    del node_data["extends"]
            
        resolved_edges = []
        resolved_edges.extend(self.contains_edges)
        
        total_calls = len(self.unresolved_calls)
        print(f"Resolving calls... Found exactly {total_calls} unresolved edges.")
        
        for i, (caller, temp_target) in enumerate(self.unresolved_calls):
            # 3. LIVE TRACKER: Shows the exact node currently being processed on the same line
            if i % 250 == 0:
                # Pad to overwrite old text, use \r to return carriage to start of line
                sys.stdout.write(f"\r[{i}/{total_calls}] Processing: {temp_target[:60]:<60} (Hits: {self.hits})")
                sys.stdout.flush()
                
            true_target = self.resolve_target(temp_target)
            
            if not true_target.startswith("EXTERNAL") and not true_target.startswith("ERROR"):
                if true_target in self.definitions:
                    resolved_edges.append({
                        "type": "calls",
                        "source": caller,
                        "target": true_target
                    })
        
        # Clear the live tracker line and finish
        sys.stdout.write("\r" + " " * 200 + "\r")
        print(f"✅ Finished! Final Cache Hits: {self.hits} | Misses: {self.misses}")
        return resolved_edges