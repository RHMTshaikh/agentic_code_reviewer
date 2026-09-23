from typing import List, Tuple

from langgraph.graph import StateGraph, START, END
from agentic_code_reviewer.clients.client_interface import ClientInterface
from agentic_code_reviewer.schemas.state import AgentState
from agentic_code_reviewer.agents.arbitrator import arbitrator_node
from agentic_code_reviewer.agents import AgentFactory
from agentic_code_reviewer.agents.system_prompts import SECURITY_SYS_PROMPT, ARCHITECT_SYS_PROMPT, LOGIC_SYS_PROMPT

def default_code_review_agent(client: ClientInterface) -> Tuple[StateGraph, dict]:
    """
    Creates a default code review agent workflow with security, architecture, and logic critics.
    Returns a tuple of the compiled workflow and the system prompts.
    """
    
    security_critic_factory = AgentFactory(
        agent_name="security_critic",
        agent_category="SECURITY",
        system_prompt=SECURITY_SYS_PROMPT,
        client=client
    )
    architecture_critic_factory = AgentFactory(
        agent_name="architecture_critic",
        agent_category="ARCHITECTURE",
        system_prompt=ARCHITECT_SYS_PROMPT,
        client=client
    )
    logic_critic_factory = AgentFactory(
        agent_name="logic_critic",
        agent_category="LOGIC",
        system_prompt=LOGIC_SYS_PROMPT,
        client=client
    )

    agent_factories = [
        security_critic_factory,
        architecture_critic_factory,
        logic_critic_factory
    ]

    return create_code_review_agent(agent_factories)

def create_code_review_agent(agent_factories: List[AgentFactory]) -> Tuple[StateGraph, dict]:
    """
    Creates a code review agent workflow with the given agent factories.
    Returns a tuple of the compiled workflow and the system prompts.
    """
    
    workflow = StateGraph(AgentState)
    
    workflow.add_node("arbitrator", arbitrator_node)

    # Register Nodes
    for agent_factory in agent_factories:
        agent_name = agent_factory.agent_name
        agent = agent_factory.make_agent()
        workflow.add_node(agent_name, agent)
        workflow.add_edge(START, agent_name)
        workflow.add_edge(agent_name, "arbitrator")

    # Terminate
    workflow.add_edge("arbitrator", END)
    
    system_prompts = {factory.agent_name: factory.system_prompt for factory in agent_factories}
    
    return workflow.compile(), system_prompts