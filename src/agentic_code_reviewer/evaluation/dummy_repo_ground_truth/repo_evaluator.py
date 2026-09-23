from pathlib import Path
import subprocess
import time

from agentic_code_reviewer.evaluation.utils import run_git

class RepoEvaluator:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.ground_truths_file = self.repo_path / "eval_ground_truth.json"
    
    def branches(self):
        """
        Get a list of all local branches in the specified Git repository.
        """
        
        try:
            # 1. Fetch the list of all local branches cleanly
            # --format='%(refname:short)' returns just the branch names without asterisks or spaces
            result = run_git(cwd=self.repo_path, args=["branch", "--format=%(refname:short)"])
            branches = [b.strip() for b in result.split('\n') if b.strip()]
            return branches
        except subprocess.CalledProcessError as e:
            print(f"Error fetching branches: {e.stderr}")
            return []
        
    def checkout_branch(self, branch_name: str):
        """
        Checkout a specific branch in the Git repository.
        """
        try:
            run_git(cwd=self.repo_path, args=["checkout", branch_name])
        except subprocess.CalledProcessError as e:
            print(f"Error checking out branch {branch_name}: {e.stderr}")
            raise
        
    def get_ground_truth_from_branch(self, branch_name: str):
        """
        Get the ground truth for a specific branch from the JSON file.
        """
        if not self.ground_truths_file.exists():
            raise FileNotFoundError(f"Ground truth file {self.ground_truths_file} does not exist.")
        
        import json
        with open(self.ground_truths_file, "r", encoding="utf-8") as f:
            ground_truths = json.load(f)
            
        if not ground_truths.get(branch_name):
            return "No ground truth available for this branch.\n"

        ground_truth_text = ""
        for issue in ground_truths.get(branch_name):
            ground_truth_text += f"Issue ID: {issue['issue_id']}\n"
            ground_truth_text += f"File: {issue['file']}\n"
            ground_truth_text += f"Severity: {issue['severity']}\n"
            ground_truth_text += f"Difficulty: {issue['difficulty']}\n"
            ground_truth_text += f"Category: {issue['category']}\n"
            ground_truth_text += f"Description: {issue['description']}\n"
            ground_truth_text += "-"*100
            ground_truth_text += "\n\n"

        return ground_truth_text
    
    def setup_for_branch(self, branch_name: str, main_branch: str = "main"):
        """
        Prepare the repository for evaluation by checking out the specified branch
        and staging changes as if they were made on top of the main branch.
        """
        try:
            # 1. CLEANUP: Destroy any leftover changes from the previous iteration
            run_git(cwd=self.repo_path, args=["reset", "--hard"])
            run_git(cwd=self.repo_path, args=["clean", "-fd"])  # Removes untracked files and directories
            
            # 2. GET TO THE DESIRED STATE:
            # Checkout the branch without moving the actual branch pointer
            run_git(cwd=self.repo_path, args=["checkout", "--detach", branch_name])
            
            # Move HEAD to main, but leave the staging area and working directory as the feature branch
            run_git(cwd=self.repo_path, args=["reset", "--soft", main_branch])
            
            # Verify the staging area
            status = run_git(cwd=self.repo_path, args=["status", "-s"])
            print(f"Staged changes ready for analysis:\n{status}")
            
        except subprocess.CalledProcessError as e:
            print(f"Error setting up for branch {branch_name}.\nGit says:\n{e.stderr}")
            raise
    
    def restore_to_main(self, main_branch: str = "main"):
        """
        Restore the repository back to the main branch and clean up any changes.
        """
        try:
            print("\nCleaning up and restoring to main...")
            run_git(cwd=self.repo_path, args=["reset", "--hard"])
            run_git(cwd=self.repo_path, args=["clean", "-fd"])
            run_git(cwd=self.repo_path, args=["checkout", main_branch])
        except subprocess.CalledProcessError as e:
            print(f"Error restoring to main. Git says:\n{e.stderr}")
            raise
    

if __name__ == "__main__":
    # Example usage
    local_repo_path = Path(r'../buggy_fintech_portfolio_manager').absolute().resolve()
    
    repo_evaluator = RepoEvaluator(local_repo_path)
    
    for branch in repo_evaluator.branches():
        print(f"Evaluating branch: {branch}")