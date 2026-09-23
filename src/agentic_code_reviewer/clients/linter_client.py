from collections import defaultdict
from pathlib import Path
import subprocess
import json
import os
from typing import List, Dict

def run_ruff_linter(file_path: str) -> List[Dict[str, str]]:
    """
    Executes Ruff against a specific file and extracts the findings.
    """
    if not os.path.exists(file_path):
        return [{"error": f"File {file_path} not found for linting."}]

    try:
        # Run ruff check with JSON output formatting
        result = subprocess.run(
            ["ruff", "check", file_path, "--output-format=json"],
            capture_output=True,
            text=True
        )
        
        if not result.stdout.strip():
            return []
            
        ruff_findings = json.loads(result.stdout)
        
        return ruff_findings  # Return both clean and raw findings for further processing

    except Exception as e:
        return [{"error": f"Linter execution failed: {str(e)}"}]

def format_errors_for_llm(ruff_json_array, root_path: str) -> str:
    # Group errors by filename
    grouped = defaultdict(list)
    for error in ruff_json_array:
        filename = Path(error["filename"]).resolve()
        filename = Path(filename).relative_to(Path(root_path).resolve())
        line = error["location"]["row"]
        msg = error["message"]
        code = error["code"]
        grouped[filename].append(f"* Line {line}: {msg} ({code})")
        
    # Build the string
    output = []
    for file, errors in grouped.items():
        output.append(f"### {file}")
        output.extend(errors)
        output.append("") # blank line
        
    markdown_output = "<KnownErrors>\n"
    markdown_output += "\n".join(output)
    markdown_output += "</KnownErrors>\n"

    return markdown_output

def generate_linter_report(file_path: str) -> str:
    """
    Generates a formatted linter report for a given file.
    """
    ruff_findings = run_ruff_linter(file_path)
    
    if not ruff_findings:
        return f"No linting issues found in {file_path}."
    
    if "error" in ruff_findings[0]:
        return f"Error during linting: {ruff_findings[0]['error']}"
    
    return format_errors_for_llm(ruff_findings, file_path)

if __name__ == "__main__":
    test_file = r"../document_align/main.py"
    ruff_findings = run_ruff_linter(test_file)
    print(generate_linter_report(test_file))