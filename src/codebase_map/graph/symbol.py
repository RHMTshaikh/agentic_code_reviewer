# src\codebase_map\graph\symbol.py
import re

class Symbol:
    def __init__(self, symbol: str):
        self.symbol_str = symbol
        self.type = self._type(symbol)
        self.function_name = self._function_name(symbol)
        self.class_name = self._class_name(symbol)
        self.scope = self._scope(symbol)
        self.name = self._name(symbol)
        # self.file = None #there is no consistent method to extract the file path from the symbol string, so we will leave it as None for now
    
    @classmethod   
    def _type(cls, symbol_str: str):
        if symbol_str.endswith('#'):
            return 'class'
        elif '#' in symbol_str and symbol_str.endswith('().'):
            return 'class_method'
        elif symbol_str.endswith('().'):
            return 'function'

    @classmethod
    def _function_name(cls, symbol_str: str):
        if cls._type(symbol_str) == 'class_method':
            return symbol_str.split('/')[-1].split('#')[1].removesuffix('().')
        elif cls._type(symbol_str) == 'function':
            return symbol_str.split('/')[-1].removesuffix('().').split('.')[-1]

    @classmethod
    def _class_name(cls, symbol_str: str):
        if cls._type(symbol_str) == 'class':
            return symbol_str.split('/')[-1].removesuffix('#')
        elif cls._type(symbol_str) == 'class_method':
            return symbol_str.split('/')[-1].split('#')[0]
    
    @classmethod
    def _scope(cls, symbol_str: str):
        _, class_or_function = symbol_str.split('/', 1)
        parts = re.split(r'[`.#()]', class_or_function)
        parts = [part for part in parts if part]  # Remove empty strings
        return '.'.join(parts)
    
    @classmethod
    def _name(cls, symbol_str: str):
        if cls._type(symbol_str) == 'class':
            return cls._class_name(symbol_str)
        elif cls._type(symbol_str) == 'class_method':
            return cls._function_name(symbol_str)
        elif cls._type(symbol_str) == 'function':
            return cls._function_name(symbol_str)
    

    def __str__(self):
        return f"Symbol(type={self.type}, function_name={self.function_name}, class_name={self.class_name}, address={self.scope})"


if __name__ == "__main__":
    symbol_str = "python document_align 0.1.0 `warp.line`/deform_image_randomly().inner_function()."
    symbol_str = "scip-python python document-align 0.1.0 warp/deform_image_randomly()."
    symbol_str = "scip-python python document-align 0.1.0 `warp.packageA`/funcA()."
    symbol = Symbol(symbol_str)
    print(symbol)