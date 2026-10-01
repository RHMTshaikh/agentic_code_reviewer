import subprocess
from pathlib import Path

from agentic_code_reviewer.clients import *
from agentic_code_reviewer.evaluation.utils import clean_evaluation_scores_file, update_scores, run_git
from agentic_code_reviewer.agents.evaluator import evaluator_agent
from agentic_code_reviewer.agents import AgentFactory
from agentic_code_reviewer import run_code_review
from agentic_code_reviewer.evaluation.utils import get_all_branches
from agentic_code_reviewer.evaluation.dummy_repo_ground_truth.repo_evaluator import RepoEvaluator
from agentic_code_reviewer.my_langgraph import create_code_review_agent, default_code_review_agent
from agentic_code_reviewer.paths import REPORTS_DIR_PATH, EVALUATIONS_DIR_PATH, MODELS_REGISTRY_FILE_PATH
from agentic_code_reviewer.schemas.state import EvaluatorResponse


# variables to evaluate
# system prompts for each agent
# models to use for review and evaluation


if __name__ == "__main__":
    local_repo_path = Path(r'../buggy_fintech_portfolio_manager').absolute().resolve()
    gemini_models = GeminiClient().show_models()
    gemini_model = gemini_models[7]
    print(f"Using Gemini model: {gemini_model}")
    # review_client = OpenAIClient()
    # review_client = GeminiClient(model_name=gemini_model)
    review_client = GroqClient(model_name="openai/gpt-oss-120b")
    # review_client = MistralClient()
    # review_client = OpenRouterClient()
    # review_client = CerebrasClient()
    
    # eval_client = OpenAIClient()
    eval_client = GeminiClient(model_name=gemini_model)
    # eval_client = GroqClient()
    # eval_client = MistralClient()
    # eval_client = OpenRouterClient()
    # eval_client = CerebrasClient()
    
    if not review_client.ping():
        raise RuntimeError(f"⚠️ Review client {review_client.__class__.__name__} is not reachable. Please check your API key and network connection.")
    
    if not eval_client.ping():
        raise RuntimeError(f"⚠️ Evaluation client {eval_client.__class__.__name__} is not reachable. Please check your API key and network connection.")

    agent, system_prompts = default_code_review_agent(review_client)

    output_dir = Path("outputs")
    
    clean_evaluation_scores_file()
    
    repo_evaluator = RepoEvaluator(local_repo_path)
    
    # 3. Iteratively checkout each branch
    for branch in repo_evaluator.branches():
        print(f"\n\n=== Evaluating branch: {branch} ===\n\n")
        try:
            repo_evaluator.setup_for_branch(branch)
            
            final_state = run_code_review(
                agent=agent,
                absolute_project_path=local_repo_path,
                report_dir=REPORTS_DIR_PATH / f"{review_client.__class__.__name__}_reports",
                require_linter=False
            )
            
            critic_input = (
                f"{AgentFactory.make_user_prompt(final_state)}\n\n" +
                "\n\n".join(f"System Prompt for {agent_name}:\n{system_prompt}" for agent_name, system_prompt in system_prompts.items())
            )
            critic_output = final_state.get("final_markdown_report", "")

            ground_truth = repo_evaluator.get_ground_truth_from_branch(branch)
            
            scores = evaluator_agent(
                time_stamp=final_state.get("time_stamp"),
                critic_input=critic_input,
                critic_output=critic_output,
                ground_truth=ground_truth,
                client=eval_client,
                eval_log_path=EVALUATIONS_DIR_PATH / f"{eval_client.model_name.split('/')[-1].replace(':', '-')}" / f"name_{local_repo_path.name}" / f"branch_{branch}.log",
                error_log_path=EVALUATIONS_DIR_PATH / "errors" / f"{eval_client.model_name.split('/')[-1].replace(':', '-')}" / f"name_{local_repo_path.name}" / f"branch_{branch}.log",
                schema=EvaluatorResponse,
                branch_name=branch
            )
            
            if scores is not None:
                update_scores(scores.model_dump())
                
        except subprocess.CalledProcessError as e:
            print(f"Failed to setup for branch {branch}. Error:\n{e.stderr}")

    repo_evaluator.restore_to_main()
