from google.protobuf.json_format import MessageToJson
import json
import os
import sys
import tempfile
import subprocess
from .uitility import clean_json
from . import scip_pb2
from pathlib import Path


def index_of_repo(project_path: Path):
    
    with tempfile.TemporaryDirectory() as temp_dir:
        scip_file_path = os.path.join(temp_dir, "index.scip")

        command = f"scip-python index {project_path} --output {scip_file_path}"

        # Run with shell=True to avoid the debugpy injection bug on Windows
        process = subprocess.Popen(
            command,                  # Pass the string directly
            shell=True,               # Re-enabled shell=True
            cwd=project_path,          # Set the working directory to the project path
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, 
            text=True,                
            bufsize=1                 
        )

        for line in process.stdout:
            print(line, end="") 

        # Wait for the command to finish and check if it succeeded
        process.wait()

        if process.returncode != 0:
            print(f"\n❌ Error: Process exited with code {process.returncode}", file=sys.stderr)
            sys.exit(1)
        else:
            print("\n✅ Indexing complete.")
            
        # 3. Read the binary data into a Python variable BEFORE the temp_dir is destroyed
        scip_index = scip_pb2.Index()
        with open(scip_file_path, "rb") as f:
            scip_index.ParseFromString(f.read())
            
        # 5. NOW convert the parsed Protobuf object to JSON
        json_data_str = MessageToJson(scip_index, preserving_proto_field_name=True)
        scip_json = json.loads(json_data_str)
        cleaned_json = clean_json(scip_json)

        return cleaned_json

