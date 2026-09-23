import time
from typing import Dict, Any, Type, TypeVar, Optional
from pathlib import Path

from pydantic import BaseModel

from agentic_code_reviewer.clients.client_interface import ClientInterface
from agentic_code_reviewer.schemas.state import ClientStructuredResponse, ErrorResponse, EvaluationScores, EvaluatorResponse, NodeAuditEntry, ReviewNodeAuditEntry
from agentic_code_reviewer.paths import EVALUATION_SCORES_FILE_PATH
from agentic_code_reviewer.agents.system_prompts import EVALUATOR_SYS_PROMPT


def evaluator_agent(
        time_stamp: str,
        critic_input: str, 
        critic_output: str,
        client: ClientInterface, 
        ground_truth: str = None,
        schema: Type[BaseModel] = EvaluatorResponse,
        eval_log_path: Path = None,
        error_log_path: Path = None,
        branch_name: str = None
    ) -> Optional[EvaluationScores]:

    user_prompt = (
        f"CRITIC INPUT:\n{critic_input}\n\n"
        f"CRITIC OUTPUT:\n{critic_output}\n\n"
        f"GROUND TRUTH:\n{ground_truth}\n\n" if ground_truth else ""
    )
    
    start_time = time.perf_counter()
    client_structured_response = client.invoke_structured(EVALUATOR_SYS_PROMPT, user_prompt, schema=schema)
    latency = (time.perf_counter() - start_time) * 1000
    
    response = client_structured_response.response

    total_tokens = client_structured_response.total_tokens
    upload_tokens = client_structured_response.upload_tokens
    download_tokens = client_structured_response.download_tokens
    model_name = client_structured_response.model_name
    
    if not eval_log_path.exists():
        eval_log_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(eval_log_path, "a", encoding="utf-8") as f:
        f.write(f"Time Stamp: {time_stamp}\n")
        f.write(f"Branch Name: {branch_name}\n")
        f.write(f"Model: {model_name}\n")
        f.write(f"Latency: {latency:.2f} ms\n")
        f.write(f"Total Tokens: {total_tokens}\n")
        f.write(f"Upload Tokens: {upload_tokens}\n")
        f.write(f"Download Tokens: {download_tokens}\n")
        f.write(f"GROUND TRUTH:\n{ground_truth}" if ground_truth else "")
        f.write(f"\n\n")
        f.write(f"RESPONSE:\n")
        f.write(parse_basemodel_response("", response, indent_level=1))
        f.write("\n" + "="*100 + "\n\n")
    
    
    
    if ClientInterface.is_error_response(response):
        # save user prompt
        error_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(error_log_path, "a", encoding="utf-8") as f:
            f.write(str(response))
            
        return None

    return response.scores


from typing import Any
from pydantic import BaseModel

def parse_basemodel_response(text: str, data: Any, indent_level: int = 0) -> str:
    """
    Parse a Pydantic BaseModel (or a nested dict/list) into a formatted string representation. 
    Recursively processes nested structures and prints final primitive values.
    """
    indent = "  " * indent_level
    
    # 1. If it is a Pydantic model, convert it to a dictionary
    if isinstance(data, BaseModel):
        data = data.model_dump()

    # 2. Handle Dictionaries (which includes dumped nested BaseModels)
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                # It's a nested structure, print the key and recurse deeper
                text += f"{indent}{key}:\n"
                text = parse_basemodel_response(text, value, indent_level + 1)
            else:
                # It's a final value (string, int, float, bool, None)
                text += f"{indent}{key}: {value}\n"
                
    # 3. Handle Lists
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                # Nested structure inside a list
                text = parse_basemodel_response(text, item, indent_level + 1)
            else:
                # Final value inside a list
                text += f"{indent}- {item}\n"
                
    return text