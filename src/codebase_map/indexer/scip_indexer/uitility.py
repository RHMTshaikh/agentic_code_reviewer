def clean_json(json_data):
    """
    Cleans the JSON data to only include relevant fields for analysis.
    Filters out occurrences and symbols that contain 'local' or 'python-stdlib'.
    """
    cleaned_data = {
        "metadata": json_data.get("metadata", {}),
        "documents": []
    }

    for doc in json_data.get("documents", []):
        # Filter occurrences
        filtered_occurrences = [
            {
                'line': occ.get('range', [0, 0, 0])[0],
                'symbol': occ.get('symbol', '').replace('scip-python ', ''),
                'symbol_roles': occ.get('symbol_roles', 0),
                'range': (occ.get('enclosing_range', [0, 0, 0, 0])[0], occ.get('enclosing_range', [0, 0, 0, 0])[2]) if 'enclosing_range' in occ else None
            }
            for occ in doc.get("occurrences", [])
            if 'local' not in occ.get("symbol", "") 
                and occ.get("symbol", "").split(' ')[2] not in ["python-stdlib","numpy", "pandas", "scipy", "matplotlib", "sklearn", "torch", "tensorflow"]
                and not occ.get("symbol", "").endswith(")") # remove all the parameters
                and not (occ.get("symbol", "").endswith(".") and not occ.get("symbol", "").endswith(").")) # remove all the class properties
                and not 'numpy.' in occ.get("symbol", "")
                and not 'torch.' in occ.get("symbol", "")
                and not '__init__' in occ.get("symbol", "")
        ]

        cleaned_doc = {
            "relative_path": doc.get("relative_path", ""),
            "occurrences": filtered_occurrences,
            # "symbols": filtered_symbols
        }

        cleaned_data["documents"].append(cleaned_doc)

    return cleaned_data
