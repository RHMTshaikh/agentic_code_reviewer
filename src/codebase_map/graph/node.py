# src\codebase_map\graph\node.py
class  Node:
    def __init__(self, name: str, type: str, fqn: str = '', range: tuple[int, int] = None, abs_path: str = None):
        self.name: str = name
        self.type: str = type # 'dir', 'file', 'function', 'class', 'class_method'
        self.fqn: str = fqn
        self.range: tuple[int, int] = range
        self.fqn: str = fqn
        self.abs_path: str = abs_path
        self.contains: set['Node'] = set()  # List of child nodes
        self.calls: set['Node'] = set()  # List of nodes that this node calls
        self.called_by: set['Node'] = set()  # List of nodes that call this node
    
    def add_child(self, other_node: 'Node'):
        self.contains.add(other_node)

    def add_called_by(self, other_node: 'Node'):
        self.called_by.add(other_node)

    def add_calls(self, other_node: 'Node'):
        self.calls.add(other_node)
    
    def parent_fqn(self):
        if not self.fqn:
            return None
        parts = self.fqn.split('.')
        if len(parts) <= 1:
            return ''
        return '.'.join(parts[:-1])
    
    def parent_name(self):
        if not self.fqn:
            return None
        parts = self.fqn.split('.')
        if len(parts) <= 1:
            return ''
        return parts[-2]  # Return the second last part as the parent name
    
    # 1. Add a __repr__ method so nodes look nice when inside sets/lists
    def __repr__(self):
        return f"Node({self.fqn})"
    
    # 2. Update __str__ to safely print the names/addresses of the connected nodes
    def __str__(self):
        # Extract just the addresses (or symbols) to prevent massive recursive outputs
        calls_list = [n.fqn.split('.')[-1] for n in self.calls]
        called_by_list = ['.'.join(n.fqn.split('.')[-2:]) for n in self.called_by]
        
        return f"{self.type} - {self.fqn}\n  CALLS - {calls_list}\n  CALLED_BY - {called_by_list}\n  CONTAINS - {[n.fqn.split('.')[-1] for n in self.contains]}"
