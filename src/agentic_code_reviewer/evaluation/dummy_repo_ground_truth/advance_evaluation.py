import subprocess
from pathlib import Path

from agentic_code_reviewer.clients import *
from agentic_code_reviewer.clients.client_interface import ClientInterface
from agentic_code_reviewer.evaluation.utils import clean_evaluation_scores_file, update_scores, run_git
from agentic_code_reviewer.agents.evaluator import evaluator_agent
from agentic_code_reviewer.agents import AgentFactory
from agentic_code_reviewer import run_code_review
from agentic_code_reviewer.evaluation.utils import get_all_branches
from agentic_code_reviewer.evaluation.dummy_repo_ground_truth.repo_evaluator import RepoEvaluator
from agentic_code_reviewer.my_langgraph import create_code_review_agent, default_code_review_agent
from agentic_code_reviewer.paths import MODELS_REGISTRY_FILE_PATH, REPORTS_DIR_PATH, EVALUATIONS_DIR_PATH
from agentic_code_reviewer.schemas.state import EvaluatorResponse

# variables to evaluate
# system prompts for each agent
# models to use for review and evaluation


if __name__ == "__main__":
    local_repo_path = Path(r'../buggy_fintech_portfolio_manager').absolute().resolve()
    gemini_models = GeminiClient().show_models()
    gemini_model = gemini_models[8]
    print(f"Using Gemini model: {gemini_model}")
    # review_client = OpenAIClient()
    # review_client = GeminiClient(model_name=gemini_model)
    # review_client = GroqClient()
    # review_client = MistralClient()
    # review_client = OpenRouterClient()
    # review_client = CerebrasClient()
    
    # eval_client = OpenAIClient()
    eval_client = GeminiClient(model_name=gemini_model)
    # eval_client = GroqClient()
    # eval_client = MistralClient()
    # eval_client = OpenRouterClient()
    # eval_client = CerebrasClient()
    
    clients_registry: dict[str, type[ClientInterface]] = {
        "OpenAIClient": OpenAIClient,
        "GeminiClient": GeminiClient,
        "GroqClient": GroqClient,
        "MistralClient": MistralClient,
        "OpenRouterClient": OpenRouterClient,
        "CerebrasClient": CerebrasClient
    }

    clients_cache: dict[str, ClientInterface] = dict()

    if not eval_client.ping():
        raise RuntimeError(f"⚠️ Evaluation client {eval_client.__class__.__name__} is not reachable. Please check your API key and network connection.")

    output_dir = Path("outputs")
    
    clean_evaluation_scores_file()
    
    repo_evaluator = RepoEvaluator(local_repo_path)

    with open(MODELS_REGISTRY_FILE_PATH, "r", encoding="utf-8") as f:
        import json
        models_registry = json.load(f)
    
    client_modle_list = [(client_name, model_name) for client_name, models_list in models_registry.items() for model_name in models_list]
    
    # I'm going to iterate our models in the inner loop of the branch loop that's we can Reduce the request per minute and token per minute rate limits on the client servers.
    # So that we don't create multiple clients we are going to cash the clients.
    # 3. Iteratively checkout each branch
    try:
        for branch in repo_evaluator.branches():
            print(f"\n\n=== Evaluating branch: {branch} ===\n\n")
            repo_evaluator.setup_for_branch(branch)
            tested_models = set()  # Keep track of models that have already been tested for this branch

            for client_name, model_name in client_modle_list:
                actual_model_name = model_name.split("/")[-1] # openai/gpt-oss-120b  # Extract the actual model name from the full path

                if actual_model_name in tested_models:
                    continue  # Skip this model as it has already been tested for this branch

                if client_name in clients_cache:
                    review_client = clients_cache.get(client_name)
                    review_client.model_name = model_name  # Update the model name for the existing client
                else:
                    client_class = clients_registry[client_name]
                    review_client = client_class(model_name=model_name)
                    clients_cache[client_name] = review_client  # Cache the client for future use

                if not review_client.ping():
                    continue  # Skip this client and move to the next one
                
                agent, system_prompts = default_code_review_agent(review_client)
                
                final_state = run_code_review(
                    agent=agent,
                    absolute_project_path=local_repo_path,
                    report_dir=REPORTS_DIR_PATH / f"{review_client.__class__.__name__}_reports",
                    require_linter=False
                )

                tested_models.add(actual_model_name) 
                
                critic_input = (
                    f"{AgentFactory.make_user_prompt(final_state)}\n\n" +
                    "\n\n".join(f"System Prompt for {agent_name}:\n{system_prompt}" for agent_name, system_prompt in system_prompts.items())
                )
                critic_output = final_state.get("final_markdown_report", "")

                ground_truth = repo_evaluator.get_ground_truth_from_branch(branch)
                
                print(f"\n\n=== Evaluating branch: {branch} with model: {model_name} ===\n\n")
                scores = evaluator_agent(
                    time_stamp=final_state.get("time_stamp"),
                    critic_input=critic_input,
                    critic_output=critic_output,
                    ground_truth=ground_truth,
                    client=eval_client,
                    eval_log_path=EVALUATIONS_DIR_PATH / f"{model_name.split('/')[-1].replace(':', '-')}" / f"name_{local_repo_path.name}" / f"branch_{branch}.log",
                    error_log_path=EVALUATIONS_DIR_PATH / "errors" / f"{model_name.split('/')[-1].replace(':', '-')}" / f"name_{local_repo_path.name}" / f"branch_{branch}.log",
                    schema=EvaluatorResponse,
                    branch_name=branch
                )
                if scores is not None:
                    print(f"✅ Evaluation scores for branch '{branch}' with model '{model_name}': {scores.model_dump()}")
                    update_scores(scores.model_dump())
                else:
                    print(f"⚠️ Evaluation failed for branch '{branch}' with model '{model_name}'. Check the error log for details.")
                
    finally:
        repo_evaluator.restore_to_main()