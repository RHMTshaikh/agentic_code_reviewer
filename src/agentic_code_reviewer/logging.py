from pathlib import Path

from agentic_code_reviewer.schemas.state import CriticResponse, ReviewNodeAuditEntry


def log(
        time_stamp: str, 
        system_prompt: str, 
        user_prompt: str, 
        response: CriticResponse, 
        audit_trail: ReviewNodeAuditEntry, 
        log_path: Path
    ) -> int:
    """
    Logs the system prompt, user prompt, response, and tokens used to a file in the logs directory.
    Each log entry is appended to the file named {file_name}.txt in the logs directory.
    Parameters:
        time_stamp: Unique timestamp for the log entry.
        system_prompt (str): The system prompt sent to the LLM.
        user_prompt (str): The user prompt sent to the LLM.
        response (CriticResponse): The response received from the LLM.
        audit_trail (ReviewNodeAuditEntry): The audit trail containing token usage information.
        log_path (Path): The path to the log file.
    Returns:
        The line number of the log entry in the log file.
    """

    log_entry = (
        f"\n{'='*50}\n"
        f"--- LOG ENTRY {time_stamp} ---\n"
        f"Audit Trail: {audit_trail.model_dump_json(indent=2)}\n"
        f"System Prompt: {system_prompt}\n"
        f"User Prompt: {user_prompt}\n"
        f"Response: {response.model_dump_json(indent=2)}\n"
    )
    line_number = 0

    with open(log_path, "a+", encoding="utf-8") as f:
        f.seek(0)
        line_number = sum(1 for _ in f)
        f.write(log_entry)

    return line_number + 3