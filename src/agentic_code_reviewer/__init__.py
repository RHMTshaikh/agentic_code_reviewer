from datetime import datetime
from pathlib import Path

from langgraph.graph import StateGraph

from agentic_code_reviewer.clients.client_interface import ClientInterface
from agentic_code_reviewer.schemas.state import AgentState
from agentic_code_reviewer.agents import AgentFactory
from agentic_code_reviewer.clients.linter_client import generate_linter_report
from agentic_code_reviewer.my_langgraph import create_code_review_agent, default_code_review_agent
from agentic_code_reviewer.clients import (
    OpenAIClient,
    GeminiClient,
    GroqClient,
    MistralClient,
    CerebrasClient,
    OpenRouterClient
)

from codebase_map.graph.builder import make_graph_using_scip, make_graph_using_ast
from codebase_map.graph.node import Node
from codebase_map.graph.utility import get_code_of_node
from codebase_map.git_utils import get_staged_fqns

ClientInterface._populate_models_registry()  # Load free models when the class is first defined


def make_input_state(project_path: Path, senior_custom_instructions = "", require_linter: bool = False) -> AgentState:
    """
    Placeholder for future implementation to fetch real diffs and SCIP context from a live repo.
    """
    if not (project_path / ".git").exists():
        print(f"⚠️ The directory '{project_path}' is not a Git repository. Please initialize a Git repository or provide a valid path.")
        return
    
    NODES, root_node = make_graph_using_ast(project_path)

    staged_fqns = get_staged_fqns(project_path)
    
    # find all the nodes that get affected by the staged ids
    affected_fqns: set[str] = set()
    for fqn in staged_fqns:
        node = NODES.get(fqn)
        
        if node:
            affected_fqns.update([node.fqn for node in node.calls])
            affected_fqns.update([node.fqn for node in node.called_by])
        else:
            print(f"⚠️ No node found for ID: {fqn}")
            
    modified_code = 'MODIFIED CODE SNIPPETS:\n' + '-'*50 + '\n\n'
    for fqn in staged_fqns:
        node = NODES.get(fqn)
        if node and node.range:
            code_snippet = get_code_of_node(node)
            modified_code += f" File: {Path(node.abs_path).relative_to(project_path)}\n" # do not place absolute path here but rather the relative path from the cwd
            modified_code += f"{code_snippet}\n"
    
    affected_fqns = affected_fqns - set(staged_fqns)  # Exclude modified nodes from affected nodes
    affected_fqns = sorted(affected_fqns)  # Sort for consistent output
    affected_code = 'AFFECTED CODE SNIPPETS:\n' + '-'*50 + '\n'
    for fqn in affected_fqns:
        node = NODES.get(fqn)
        if node and node.range:
            code_snippet = get_code_of_node(node)
            affected_code += f" File: {Path(node.abs_path).relative_to(project_path)}\n" # do not place absolute path here but rather the relative path from the cwd
            affected_code += f"{code_snippet}\n"
    
            
    if require_linter:
        linter_anotations = generate_linter_report(project_path)
    else:
        linter_anotations = ""

    linter_instructions = "Note: The following linter errors have already been caught by Ruff. Do NOT focus on or suggest fixes for these specific issues:\n"

    repository_context_path = (
        project_path / "repository_context.md"
        if (project_path / "repository_context.md").exists()
        else project_path / "repository_context.txt"
        if (project_path / "repository_context.txt").exists()
        else None
    )
    
    if not repository_context_path:
        print(f"⚠️ The file 'repository_context.md' or 'repository_context.txt' is missing in the project directory '{project_path}'.")
        print("The agent works best when it has access to the repository context. Please add the file and rerun the evaluation.")
    else:
        with open(repository_context_path, "r", encoding="utf-8") as f:
            repository_context = f.read()
        
    input_state: AgentState = {
        "time_stamp": datetime.now().strftime("%d-%m-%Y_%H-%M-%S"),
        "modified_code": modified_code,
        "affected_code": affected_code,
        "linter_annotations": linter_instructions + linter_anotations,
        "repository_context": repository_context,
        "senior_custom_instructions": senior_custom_instructions,
        
        "raw_findings": [],
        "node_audit_trail": [],
        "validated_findings": [],
        "dropped_findings": [],
        "final_markdown_report": ""
    }  
    
    return input_state

def save_results(final_state: AgentState, report_dir: Path ):

    # Display Node-Level Observability Trail
    print("\n" + "="*50)
    print("📊 EXECUTION AUDIT TRAIL (NODE OBSERVABILITY)")
    print(f"Timestamp: {final_state.get('time_stamp')}")
    print(f"Report Path: {report_dir}")
    print("="*50)
    for audit in final_state["node_audit_trail"]:
            print(f"• Node: {audit.node_name:<22} | Latency: {audit.latency_ms:>6.2f} ms | Findings: {audit.findings_generated} | Upload Tokens: {audit.upload_tokens} | Download Tokens: {audit.download_tokens} | Total Tokens: {audit.total_tokens} | Model: {audit.model_name}")

    # Save and Output Report
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "review_report.md"
    with open(report_path, "a", encoding="utf-8") as f:
        f.write(final_state["final_markdown_report"])

    print("\n" + "="*50)
    print(f"✅ Review complete! Output saved to: {report_path}")
    print("="*50)

def run_code_review(
        absolute_project_path: str, 
        agent: StateGraph = None,
        report_dir: Path = Path.cwd() / "reports", 
        senior_custom_instructions: str = "",
        require_linter: bool = False
    ) -> AgentState:
    """
    Runs the code review process using the provided agent factories and project path.
    Parameters:
        project_path (str): The path to the project to be reviewed
        agent_factories (list): A list of AgentFactory instances to be used in the review
        report_dir (Path): The directory where the review report will be saved
        senior_custom_instructions (str): Custom instructions for the senior developer
        require_linter: bool = False
    """
    absolute_path = Path(absolute_project_path).resolve()
    input_state = make_input_state(absolute_path, senior_custom_instructions=senior_custom_instructions, require_linter=require_linter)
    
    final_state = agent.invoke(input_state)
    
    save_results(final_state, report_dir)
    
    return final_state
    
    
if __name__ == "__main__":
    project_path = "sample_project"
    input_state = make_input_state(project_path)