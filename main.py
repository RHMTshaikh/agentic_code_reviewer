if __name__ == "__main__":
    from pathlib import Path

    from agentic_code_reviewer import run_code_review
    from agentic_code_reviewer.agents import AgentFactory
    from agentic_code_reviewer.clients.client_interface import ClientInterface
    from agentic_code_reviewer.clients import (
        OpenAIClient,
        GeminiClient,
        GroqClient,
        MistralClient,
        CerebrasClient,
        OpenRouterClient
    )
    from agentic_code_reviewer import create_code_review_agent, default_code_review_agent
    from codebase_map import launch_gui
    from agentic_code_reviewer.paths import REPORTS_DIR_PATH


    project_path = r'../document_align'
    project_path = r'../huggingface_transformer_clone/transformers/src/transformers/generation'
    project_path = r'../buggy_fintech_portfolio_manager'

    absolute_path = Path(project_path).resolve()
    
    client = GeminiClient("gemini-flash-lite-latest")
    # client = OpenAIClient()
    # client = GroqClient()
    # client = MistralClient()
    # client = CerebrasClient()
    # client = OpenRouterClient()
    
    agent, system_prompts = default_code_review_agent(client=client)
    
    final_state = run_code_review(
        agent=agent,
        absolute_project_path=project_path,
        report_dir=REPORTS_DIR_PATH / f"{client.__class__.__name__}_reports",
        require_linter=False
    )