import subprocess
from pathlib import Path

from agentic_code_reviewer.clients import *
from agentic_code_reviewer.evaluation.utils import clean_evaluation_scores_file, update_scores
from agentic_code_reviewer.my_langgraph import create_code_review_agent
from .github_utils import RepoEvaluator
from agentic_code_reviewer.agents.evaluator import evaluator_agent
from agentic_code_reviewer.agents import AgentFactory
from agentic_code_reviewer import run_code_review
from agentic_code_reviewer.environment_manager import get_or_prompt_github_token
from agentic_code_reviewer.paths import REPORTS_DIR_PATH

if __name__ == "__main__":
    github_token = get_or_prompt_github_token()
    local_repo_path = Path(r'../huggingface_transformer_clone/transformers').absolute().resolve()
    gemini_models = GeminiClient().show_models()
    gemini_model = gemini_models[7]
    print(f"Using Gemini model: {gemini_model}")
    # review_client = OpenAIClient()
    review_client = GeminiClient(model_name=gemini_model)
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
    
    if not review_client.ping():
        raise RuntimeError(f"⚠️ Review client {review_client.__class__.__name__} is not reachable. Please check your API key and network connection.")
    
    if not eval_client.ping():
        raise RuntimeError(f"⚠️ Evaluation client {eval_client.__class__.__name__} is not reachable. Please check your API key and network connection.")

    logic_critic_factory = AgentFactory(
        agent_name="logic_critic",
        agent_category="LOGIC",
        system_prompt = (
            "You are an elite Senior Staff Engineer specializing in Logic and Edge-Case code review. "
            "Your objective is to trace variable states, loop invariants, and execution flows to identify catastrophic logic failures. "
            "Focus strictly on: unhandled exceptions, null/undefined dereferences, off-by-one errors, race conditions, and boundary bypasses. "
            "Do not comment on style, naming, or architecture. "
            "EXECUTION INSTRUCTIONS: "
            "1. Trace the data flow step-by-step internally. "
            "2. If a logic flaw is found, provide the exact line number, the sequence of events that triggers it, and a minimal fix. "
            "3. If no high-confidence logic bugs are found, output exactly and only: 'STATUS: CLEAN'. "
            "Never invent issues to fill space."
        ),
        client=review_client
    )
    architecture_critic_factory = AgentFactory(
        agent_name="architecture_critic",
        agent_category="ARCHITECTURE",
        system_prompt = (
            "You are a Principal Software Architect conducting a structural code review. "
            "Your objective is to identify systemic design flaws that damage long-term maintainability. "
            "Focus strictly on: violations of SOLID principles, tight coupling, leaky abstractions, cyclic dependencies, and improper state management. "
            "Do not comment on micro-logic or syntax. "
            "EXECUTION INSTRUCTIONS: "
            "1. Analyze the boundaries, interfaces, and component responsibilities. "
            "2. If an architectural flaw exists, cite the specific design principle violated, explain the future scaling risk, and suggest a structural refactor. "
            "3. If the architecture is sound, output exactly and only: 'STATUS: CLEAN'. "
            "Avoid subjective nitpicking; only flag issues that objectively block scalability."
        ),
        client=review_client
    )
    security_critic_factory = AgentFactory(
        agent_name="security_critic",
        agent_category="SECURITY",
        system_prompt = (
            "You are an elite Application Security Engineer auditing code for critical vulnerabilities. "
            "Your objective is to identify exploit vectors. "
            "Enforce OWASP Top 10 standards. Focus strictly on: injection (SQL/NoSQL/Command), XSS, broken access control, insecure direct object references (IDOR), cryptographic failures, and hardcoded secrets. "
            "EXECUTION INSTRUCTIONS: "
            "1. Think like an attacker. Trace user-controlled inputs to sensitive sinks. "
            "2. If a vulnerability is found, state the CWE category, explain the exploit scenario step-by-step, and provide the secure mitigation. "
            "3. If no verifiable vulnerabilities are found, output exactly and only: 'STATUS: CLEAN'. "
            "Do not flag theoretical risks without a clear attack path."
        ),
        client=review_client
    )
    
    agent_factories=[
        logic_critic_factory,
        architecture_critic_factory,
        security_critic_factory
    ]
    
    agent = create_code_review_agent(agent_factories)

    owner="huggingface"
    repo_name="transformers"
    pr_number=46419
    pr_number=46717
    
    repo_evaluator = RepoEvaluator(
        owner,
        repo_name,
        local_repo_path,
        token=github_token
    )
    output_dir = Path("outputs")
    
    ground_truth_dict = repo_evaluator.build_ground_truth(pr_number, min_weight=2)
    # with open("outputs/ground_truth.json", "r", encoding="utf-8") as f:
    #     import json
    #     ground_truth_dict = json.load(f)
    
    eval_scores_path = Path.cwd() / "evaluation_scores.json"
    clean_evaluation_scores_file(eval_scores_path)

    for sha, commit_info in list(ground_truth_dict["commits"].items())[3:]:
        
        try:
            # 1. Aggressively clear tracked AND untracked files to prevent checkout conflicts
            repo_evaluator.run_git(["reset", "--hard"])
            repo_evaluator.run_git(["clean", "-fd"])
            
            # 2. Check out the target commit safely
            repo_evaluator.run_git(["checkout", "--detach", sha])
            
            # 3. Find the exact split point
            # NOTE: Consider extracting the PR's actual base branch dynamically in the future
            merge_base = repo_evaluator.run_git(["merge-base", "origin/main", sha]).strip()
            
            # 4. Stage the files modified by the PR up to this exact commit
            repo_evaluator.run_git(["reset", "--soft", merge_base])
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Cannot checkout or calculate merge-base for {sha}. Skipping. Details: {e}")
            # Safely remove the orphaned commit from the dictionary so it doesn't cause errors downstream
            del ground_truth_dict["commits"][sha]
            continue
    
        final_state = run_code_review(
            agent=agent,
            absolute_project_path=local_repo_path,
            report_dir=REPORTS_DIR_PATH / f"{review_client.__class__.__name__}_reports"
        )

        critic_input = (
            f"{AgentFactory.make_user_prompt(final_state)}\n\n" +
            "\n\n".join(f"{factory.agent_name}\n{factory.system_prompt}" for factory in agent_factories)
        )
        critic_output = final_state.get("final_markdown_report", "")

        github_comments = RepoEvaluator.make_ground_truth_text(commit_info)
        
        scores = evaluator_agent(
            critic_input=critic_input,
            critic_output=critic_output,
            ground_truth=github_comments,
            client=eval_client,
            error_log_path=output_dir / "evaluations" / f"owner_{owner}" / f"repo_{repo_name}" / f"pr_{pr_number}.log"
        )
        
        if scores is not None:
            update_scores(scores.model_dump(), eval_scores_file_path=eval_scores_path)  
        