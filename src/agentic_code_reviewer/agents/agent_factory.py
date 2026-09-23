import time
from typing import Dict, Any
from agentic_code_reviewer.clients.client_interface import ClientInterface
from agentic_code_reviewer.logging import log
from agentic_code_reviewer.schemas.state import AgentState, CriticResponse, ErrorResponse, ReviewNodeAuditEntry, ClientStructuredResponse

""" 
Because Langgraph needs a name with the agent function wee need to encapsulate the agent name inside the agent maker.
That's why we have this AgentFactory class which takes the agent name and returns a function that has the agent name in its closure.
"""

class AgentFactory:
    """
    Creates an agent with the specified name, role, and goals.
    
    Args:
        agent_name (str): The name of the agent.
        system_prompt (str): The system prompt for the agent.
        agent_goals (list): A list of goals for the agent.
        client (ClientInterface): The client to use for the agent.

    """
    def __init__(self, agent_name: str, agent_category: str, system_prompt: str, client: ClientInterface):
        self.agent_name = agent_name
        self.agent_category = agent_category
        self.system_prompt = system_prompt
        self.client = client

    def make_agent(self) -> Dict[str, Any]:
        def agent(state: AgentState) -> Dict[str, Any]:
            user_prompt = self.make_user_prompt(state)
            
            start_time = time.perf_counter()
            client_structured_response = self.client.invoke_structured(self.system_prompt, user_prompt, schema=CriticResponse)
            latency = (time.perf_counter() - start_time) * 1000

            response = client_structured_response.response
            total_tokens = client_structured_response.total_tokens
            upload_tokens = client_structured_response.upload_tokens
            download_tokens = client_structured_response.download_tokens
            model_name = client_structured_response.model_name
            
            if not ClientInterface.is_error_response(response):
                findings = response.findings
                for finding in findings:
                    finding.category = self.agent_category
                error = []
            else:
                findings = []
                error = [response]
                
            audit = ReviewNodeAuditEntry(
                node_name=self.agent_name,
                model_name=model_name,
                latency_ms=round(latency, 2),
                findings_generated=len(findings),
                total_tokens=total_tokens,
                upload_tokens=upload_tokens,
                download_tokens=download_tokens
            )
            log(
                time_stamp=state.get("time_stamp"),
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
                response=response,
                audit_trail=audit,
                file_name=self.agent_name
            )
            return {
                "raw_findings": findings,
                "errors": error,
                "node_audit_trail": [audit]
            }

        return agent
    
    @classmethod
    def make_user_prompt(cls, state: AgentState) -> Dict[str, Any]:
        user_prompt = (
            f"MODIFIED CODE:\n{state['modified_code']}\n\n"
            f"AFFECTED CODE:\n{state['affected_code']}\n\n"
            f"LINTER FINDINGS (DO NOT REPORT THESE):\n{state['linter_annotations']}\n"
            f"REPOSITORY CONTEXT:\n{state.get('repository_context', 'None')}\n"
            f"SENIOR INSTRUCTIONS:\n{state.get('senior_custom_instructions', 'None')}\n"
        )
        return user_prompt