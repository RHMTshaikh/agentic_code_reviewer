import subprocess
import json
from pathlib import Path

from pydantic import BaseModel

from agentic_code_reviewer.paths import EVALUATION_SCORES_FILE_PATH

def clean_evaluation_scores_file(eval_scores_file_path: Path = EVALUATION_SCORES_FILE_PATH):
    """
    Clear all previous evaluation scores
    """
    if eval_scores_file_path.exists():
        with open(eval_scores_file_path, "w", encoding="utf-8") as f:
            f.write('{}') 
    else:
        # If the file doesn't exist, create it and write an empty JSON object
        eval_scores_file_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
        with open(eval_scores_file_path, "w", encoding="utf-8") as f:
            f.write('{}')
        
        
def update_scores(scores: dict[str, float], eval_scores_file_path: Path = EVALUATION_SCORES_FILE_PATH):
    """
    Append new evaluation scores to the existing scores in the JSON file.
    """
    if not eval_scores_file_path.exists():
        # If the file doesn't exist, create it and write the initial scores
        with open(eval_scores_file_path, "w", encoding="utf-8") as f:
            json.dump(scores, f, indent=2)
    else:
        # If the file exists, read the existing scores and append the new ones
        with open(eval_scores_file_path, "r", encoding="utf-8") as f:
            prev_scores = json.load(f)
        
        for key, value in scores.items():
            if key not in prev_scores:
                prev_scores[key] = []
            prev_scores[key].append(scores[key])

        with open(eval_scores_file_path, "w", encoding="utf-8") as f:
            json.dump(prev_scores, f, indent=2)
            

def get_all_branches(repo_path: Path):
    """
    Get a list of all local branches in the specified Git repository.
    """
    try:
        # 2. Fetch the list of all local branches cleanly
        # --format='%(refname:short)' returns just the branch names without asterisks or spaces
        result = run_git(cwd=repo_path, args=["branch", "--format=%(refname:short)"])
        
        # Parse the output into a list of strings
        branches = [b.strip() for b in result.split('\n') if b.strip()]
        print(f"Found {len(branches)} branches: {branches}\n")
        return branches        
    except subprocess.CalledProcessError as e:
        print(f"Error fetching branches: {e.stderr}")
        return []


def run_git(cwd: Path, args: list[str]) -> str:
    """Executes a git command inside the local repository."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {e.stderr}")
        raise


if __name__ == "__main__":
    fake_scores = {
        "accuracy": [0.9, 0.85],
        "precision": [0.8, 0.75],
        "recall": [0.7, 0.65]
    }
    
    clean_evaluation_scores_file()
    update_scores(fake_scores)