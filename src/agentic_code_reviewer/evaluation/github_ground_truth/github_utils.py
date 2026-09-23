import requests
import subprocess
from pathlib import Path
import os
from agentic_code_reviewer.evaluation.utils import run_git

# Assign integers to establish an authority hierarchy
role_weights = {
    "OWNER": 5,
    "MEMBER": 4,
    "COLLABORATOR": 3,
    "CONTRIBUTOR": 2,
    "FIRST_TIME_CONTRIBUTOR": 1,
    "FIRST_TIMER": 0,
    "NONE": 0,
    "MANNEQUIN": 0
}

class RepoEvaluator:
    def __init__(self, owner: str, repo_name: str, local_repo_path: Path, token: str):
        self.owner = owner
        self.repo_name = repo_name
        self.local_repo_path = local_repo_path
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}

    def _get_local_code_snippet(self, file_path: str, start_line: int, end_line: int, context_buffer: int = 2) -> str:
        """Extracts code from the CURRENTLY checked-out commit on disk."""
        git_path = str(file_path).replace("\\", "/")
        start_idx = max(0, start_line - 1 - context_buffer)
        end_idx = end_line + context_buffer

        full_path = self.local_repo_path / git_path
        if not full_path.exists():
            return "<File not found in this commit state>"
            
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()[start_idx:end_idx]
            
        numbered_lines = [
            f"{line_num:6} | {line}" 
            for line_num, line in enumerate(lines, start=start_idx + 1)
        ]
            
        return "\n".join(numbered_lines)
    
    @classmethod
    def mine_evaluation_prs(cls, repo_owner: str, repo_name: str, max_files: int = 10, min_maintainer_threads: int = 2, target_count: int = None) -> list[dict]:
        """Scans a repository for small PRs with high-quality maintainer reviews."""
        
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GITHUB_TOKEN environment variable is missing.")
            
        headers = {"Authorization": f"Bearer {token}"}
        url = "https://api.github.com/graphql"
        
        # Cast a wide net: Merged PRs with at least 5 general comments
        search_str = f"repo:{repo_owner}/{repo_name} is:pr is:merged comments:>5"
        
        query = """
        query($search_str: String!, $cursor: String) {
        search(query: $search_str, type: ISSUE, first: 40, after: $cursor) {
            pageInfo { hasNextPage endCursor }
            nodes {
            ... on PullRequest {
                number
                title
                changedFiles
                reviewThreads(first: 20) {
                nodes {
                    comments(first: 10) {
                    nodes {
                        authorAssociation
                    }
                    }
                }
                }
            }
            }
        }
        }
        """
        
        golden_prs = []
        has_next_page = True
        cursor = None
        maintainer_roles = {"MEMBER", "COLLABORATOR", "OWNER"}
        
        print(f"Mining {repo_owner}/{repo_name} for high-signal PRs...\n")

        if not target_count:
            import math
            target_count = math.inf
            
        while has_next_page and len(golden_prs) < target_count:
            response = requests.post(
                url, 
                json={'query': query, 'variables': {"search_str": search_str, "cursor": cursor}}, 
                headers=headers
            )
            
            data = response.json().get("data", {}).get("search", {})
            if not data:
                break
                
            for pr in data.get("nodes", []):
                if not pr or not pr.get("changedFiles"):
                    continue
                    
                # 1. Filter by File Count Limit
                if pr["changedFiles"] > max_files:
                    continue
                    
                # 2. Filter by Maintainer Participation
                maintainer_thread_count = 0
                for thread in pr.get("reviewThreads", {}).get("nodes", []):
                    if not thread:
                        continue
                    
                    # Check if anyone in this specific thread has authority
                    has_authority = any(
                        c.get("authorAssociation") in maintainer_roles 
                        for c in thread.get("comments", {}).get("nodes", []) if c
                    )
                    
                    if has_authority:
                        maintainer_thread_count += 1
                        
                # 3. Save if it meets the authority threshold
                if maintainer_thread_count >= min_maintainer_threads:
                    golden_prs.append({
                        "number": pr["number"],
                        "changed_files": pr["changedFiles"],
                        "authoritative_threads": maintainer_thread_count,
                        "title": pr["title"]
                    })
                    
                    print(f"Found Match: PR #{pr['number']} ({pr['changedFiles']} files, {maintainer_thread_count} threads)")
                    
                    if len(golden_prs) >= target_count:
                        break
                        
            has_next_page = data.get("pageInfo", {}).get("hasNextPage", False)
            cursor = data.get("pageInfo", {}).get("endCursor")
        
        print(f"Found {len(golden_prs)} high-signal PRs in {repo_owner}/{repo_name}.")
        return golden_prs

    def _fetch_graphql_data(self, pr_number: int) -> dict:
        """Executes GraphQL queries to get the entire PR timeline, paginating through all data."""
        
        # Helper function to execute a query and handle errors
        def execute_query(query_str: str, variables: dict) -> dict:
            response = requests.post(
                "https://api.github.com/graphql",
                json={'query': query_str, 'variables': variables},
                headers=self.headers
            )
            if response.status_code != 200:
                raise Exception(f"GraphQL Network Error: {response.status_code} - {response.text}")
                
            response_data = response.json()
            if "errors" in response_data:
                import json
                error_msg = json.dumps(response_data["errors"], indent=2)
                raise ValueError(f"CRITICAL: GitHub rejected the GraphQL query:\n{error_msg}")
                
            return response_data["data"]["repository"]["pullRequest"]

        # 1. Fetch base PR metadata
        print("Fetching PR metadata...")
        base_query = """
        query($owner: String!, $name: String!, $pr_number: Int!) {
            repository(owner: $owner, name: $name) {
                pullRequest(number: $pr_number) {
                    title
                    body
                    author { login }
                }
            }
        }
        """
        pr_data = execute_query(base_query, {"owner": self.owner, "name": self.repo_name, "pr_number": pr_number})
        
        # Helper function to paginate through any GraphQL connection (list)
        def paginate_connection(connection_name: str, query_str: str) -> list:
            all_nodes = []
            has_next_page = True
            cursor = None
            
            while has_next_page:
                vars_dict = {
                    "owner": self.owner, 
                    "name": self.repo_name, 
                    "pr_number": pr_number, 
                    "cursor": cursor
                }
                data = execute_query(query_str, vars_dict)
                connection_data = data[connection_name]
                
                all_nodes.extend(connection_data["nodes"])
                has_next_page = connection_data["pageInfo"]["hasNextPage"]
                cursor = connection_data["pageInfo"]["endCursor"]
                
            return all_nodes

        # NEW: Paginate General PR Comments
        print("Paginating general PR comments...")
        pr_comments_query = """
        query($owner: String!, $name: String!, $pr_number: Int!, $cursor: String) {
            repository(owner: $owner, name: $name) {
                pullRequest(number: $pr_number) {
                    comments(first: 100, after: $cursor) {
                        pageInfo { hasNextPage endCursor }
                        nodes { 
                            author { login } 
                            authorAssociation 
                            body 
                            createdAt 
                        }
                    }
                }
            }
        }
        """
        all_pr_comments = paginate_connection("comments", pr_comments_query)

        # 2. Paginate all Commits
        print("Paginating commits...")
        commits_query = """
        query($owner: String!, $name: String!, $pr_number: Int!, $cursor: String) {
            repository(owner: $owner, name: $name) {
                pullRequest(number: $pr_number) {
                    commits(first: 100, after: $cursor) {
                        pageInfo { hasNextPage endCursor }
                        nodes { 
                            commit { 
                                oid 
                                messageHeadline 
                                message
                                committedDate
                            } 
                        }
                    }
                }
            }
        }
        """
        all_commits = paginate_connection("commits", commits_query)

        # 3. Paginate all Review Threads
        print("Paginating review threads...")
        threads_query = """
        query($owner: String!, $name: String!, $pr_number: Int!, $cursor: String) {
            repository(owner: $owner, name: $name) {
                pullRequest(number: $pr_number) {
                    reviewThreads(first: 100, after: $cursor) {
                        pageInfo { hasNextPage endCursor }
                        nodes {
                            subjectType
                            diffSide
                            path 
                            originalStartLine  # Start of old code range
                            originalLine       # End of old code range
                            comments(first: 100) {
                                nodes {
                                    author { login } 
                                    authorAssociation 
                                    body 
                                    originalCommit {
                                        oid
                                        committedDate   # <--- Gets the exact time it was applied to the tree
                                        message
                                        messageHeadline
                                    }
                                    commit { oid }
                                    createdAt
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        all_threads = paginate_connection("reviewThreads", threads_query)

        # 4. Paginate all Overarching Reviews
        print("Paginating review summaries...")
        reviews_query = """
        query($owner: String!, $name: String!, $pr_number: Int!, $cursor: String) {
            repository(owner: $owner, name: $name) {
                pullRequest(number: $pr_number) {
                    reviews(first: 100, after: $cursor) {
                        pageInfo { hasNextPage endCursor }
                        nodes {
                            author { login } 
                            authorAssociation 
                            state 
                            body
                            createdAt
                            commit {
                                oid
                                committedDate
                                message
                                messageHeadline
                            }
                        }
                    }
                }
            }
        }
        """
        all_reviews = paginate_connection("reviews", reviews_query)

        # 5. Assemble and return the final data structure
        pr_data["general_comments"] = {"nodes": all_pr_comments}
        pr_data["commits"] = {"nodes": all_commits}
        pr_data["reviewThreads"] = {"nodes": all_threads}
        pr_data["reviews"] = {"nodes": all_reviews}
        
        return pr_data
    
    def _is_commit_available_locally(self, commit_ref: str) -> bool:
        """Checks if a specific commit or reference is present in the local Git repository."""
        try:
            run_git(cwd=self.local_repo_path, args=["rev-parse", "--verify", commit_ref])
            return True
        except subprocess.CalledProcessError:
            return False
    
    def _commit_wise(self, pr_number: int, min_weight: int = 2) -> dict:
        """
        Fetches GraphQL data, chronologically checks out commits, and extracts local code snippets.
        Returns a deeply nested dictionary organized by PR -> Commits -> Threads.
        """
        print(f"Fetching chronological timeline via GraphQL for PR #{pr_number}...")
        pr_data = self._fetch_graphql_data(pr_number)
        
        # check if pr commit available locally, if not fetch it
        if not self._is_commit_available_locally(f"pr-{pr_number}"):
            print("Fetching PR commits locally...")
            run_git(cwd=self.local_repo_path, args=["fetch", "origin", f"pull/{pr_number}/head:pr-{pr_number}"])
        
        commit_registry = {}
        """
        Structure of commit_registry:
        {
            "commit_sha": {
                "time": "2024-06-01T12:34:56Z",
                "commit_message_headline": "Fix bug in XYZ",
                "commit_message": "Fix bug in XYZ",
                "threads": [
                    {
                        "file_path": "src/example.py",
                        "subject_type": "LINE" or "FILE",
                        "side": "RIGHT" or "LEFT",
                        "start_line": 11,
                        "end_line": 22,
                        "code_snippet": "...",
                        "conversation": [
                            {"author": "maintainer1", "role": "MEMBER", "feedback": "..."},
                            {"author": "contributor1", "role": "CONTRIBUTOR", "feedback": "..."}
                        ]
                    }
                ],
                "reviews" : [
                    {
                        "author": "reviewer1",
                        "role": "MEMBER",
                        "feedback": "..."
                    }
                ]
            }
        }
        """
        # 1. Register base PR commits
        for commit_node in pr_data.get("commits", {}).get("nodes", []):
            oid = commit_node["commit"]["oid"]
            commit_registry[oid] = {
                "time": commit_node["commit"]["committedDate"], 
                "commit_message": commit_node["commit"]["message"],
                "commit_message_headline": commit_node["commit"]["messageHeadline"],
                "threads": [],
                "reviews": []
            }
            
        # 2. Process Threads without overwriting
        for thread_node in pr_data.get("reviewThreads", {}).get("nodes", []):
            root_comment = thread_node.get("comments", {}).get("nodes", [])[0]
            original_commit = root_comment["originalCommit"]
            oid = original_commit["oid"]
            
            # Safely initialize if this commit was orphaned/not in the standard commit list
            if oid not in commit_registry:
                commit_registry[oid] = {
                    "time": original_commit["committedDate"],
                    "commit_message": original_commit["message"],
                    "commit_message_headline": original_commit["messageHeadline"],
                    "threads": [],
                    "reviews": []
                }
                
            commit_registry[oid]["threads"].append({
                "path": thread_node.get("path"),
                "subject_type": thread_node.get("subjectType"),
                "side": thread_node.get("diffSide"),
                "start_line": thread_node.get("originalStartLine") or thread_node.get("originalLine"),
                "end_line": thread_node.get("originalLine"),
                "code_snippet": "Not assigned",  # Placeholder; will be filled in after checkout
                "conversation": [
                    {
                        "author": c["author"]["login"],
                        "role": c["authorAssociation"],
                        "feedback": c["body"]
                    } for c in thread_node.get("comments", {}).get("nodes", []) if c.get("body") and c.get("body").strip()  # Filter out empty comments
                ]
            })
                
        # 3. Process Reviews without overwriting
        for review_node in pr_data.get("reviews", {}).get("nodes", []):
            oid = review_node["commit"]["oid"]
            
            # Safely initialize if this commit was orphaned/not in the standard commit list
            if oid not in commit_registry:
                commit_registry[oid] = {
                    "time": review_node["commit"]["committedDate"],
                    "commit_message": review_node["commit"]["message"],
                    "commit_message_headline": review_node["commit"]["messageHeadline"],
                    "threads": [],
                    "reviews": []
                }
            
            if review_node.get("body") and review_node.get("body").strip():
                commit_registry[oid]["reviews"].append({
                    "author": review_node["author"]["login"],
                    "role": review_node["authorAssociation"],
                    "feedback": review_node["body"]
                })

        general_comments = []
        """
        Structure of general_comments:
        [
            {
                "author": "maintainer1",
                "role": "MEMBER",
                "body": "...",
                "created_at": "2024-06-01T12:34:56Z"
            },
            ...
        ]
        """
        for comment in pr_data.get("general_comments", {}).get("nodes", []):
            if not comment["body"] or not comment.get("body").strip():
                continue
            weight = role_weights.get(comment.get("authorAssociation", "NONE"), 0)
            if weight >= min_weight:
                general_comments.append({
                    "author": comment["author"]["login"],
                    "role": comment["authorAssociation"],
                    "body": comment["body"],
                    "created_at": comment["createdAt"]
                })
        
        return {
            "title": pr_data["title"],
            "body": pr_data["body"],
            "author": pr_data["author"]["login"],
            "general_comments": general_comments,
            "commits": commit_registry,
        }
    
    def build_ground_truth(self, pr_number: int, min_weight: int = 2) -> dict:
        """
        Combines commit-wise data and local code snippets to produce a comprehensive ground truth.
        """
        commit_wise_data = self._commit_wise(pr_number, min_weight=min_weight)
        
        # 1. Identify commits with no threads (do this before iterating to avoid modification errors)
        commits_to_remove = [
            sha for sha, info in commit_wise_data["commits"].items() 
            if not info.get("threads")
        ]
        
        # 2. Remove them from the dictionary entirely
        for sha in commits_to_remove:
            del commit_wise_data["commits"][sha]
        
        # 3. Checkout remaining valid commits and fetch local code snippets
        for commit_sha, commit_info in commit_wise_data["commits"].items():
            try:
                # 1. Aggressively clear tracked AND untracked files to prevent checkout conflicts
                run_git(cwd=self.local_repo_path, args=["reset", "--hard"])
                run_git(cwd=self.local_repo_path, args=["clean", "-fd"])
                
                # 2. Checkout the historical commit
                run_git(cwd=self.local_repo_path, args=["checkout", "--detach", commit_sha])
            except subprocess.CalledProcessError as e:
                print(f"⚠️ Cannot checkout {commit_sha} (likely force-pushed/orphaned). Skipping.")
                # Remove it from our data so we don't process empty snippets later
                del commit_wise_data["commits"][commit_sha]
                continue
            
            for thread in commit_info["threads"]:
                type = thread.get("subject_type")
                file_path = thread.get("path")
                if type == "LINE":
                    start_line = thread.get("start_line")
                    end_line = thread.get("end_line")
                    
                    snippet = self._get_local_code_snippet(
                        file_path=file_path,
                        start_line=start_line,
                        end_line=end_line
                    )
                elif type == "FILE":
                    # For file-level threads, fetch the entire file content
                    snippet = self._get_local_code_snippet(
                        file_path=file_path,
                        start_line=1,
                        end_line=1000000  # Arbitrary large number to capture the whole file
                    )
                else:   
                    snippet = "<Unknown subject type; cannot fetch snippet>"
                    
                thread["code_snippet"] = snippet
        
        return commit_wise_data
    
    @classmethod
    def make_ground_truth_text(cls, commit_info: dict) -> str:
        """
        Converts the structured commit information into a human-readable text format.
        """
        github_comments = f"--- GITHUB COMMENTS ---\n\n"
        github_comments += f"COMMIT HEADLINE:\n {commit_info.get('commit_message_headline', '')}\n"
        github_comments += f"COMMIT MESSAGE:\n {commit_info.get('commit_message', '')}\n\n"
        
        github_comments += "THREADS:\n"
        for thread in commit_info.get("threads", []):
            # Fetch data from the 'thread' dict, not 'commit_info'
            github_comments += f"   File: {thread.get('path', '')}\n"
            if thread.get("subject_type", "") == "FILE":
                github_comments += "   this thread is on whole file.\n"
            
            side = 'new code' if thread.get('side', '') == 'RIGHT' else 'old code'
            github_comments += f"   this thread is on {side}\n"
            github_comments += "    CODE SNIPPET:\n"
            
            # Fix syntax error: Extract backslashes from f-string
            formatted_snippet = thread.get('code_snippet', '').replace('\n', '\n       ')
            github_comments += f"       {formatted_snippet}\n"
            
            github_comments += "   CONVERSATION:\n"
            for conversation in thread.get("conversation", []):
                # Fix syntax error: Extract backslashes from f-string
                formatted_feedback = conversation.get('feedback', '').replace('\n', '\n         ')
                github_comments += f"      {conversation.get('author', '')} ({conversation.get('role', '')}): {formatted_feedback}\n\n"

        github_comments += "\nREVIEWS:\n"
        for review in commit_info.get("reviews", []):
            # Fix syntax error: Extract backslashes from f-string
            formatted_review = review.get('feedback', '').replace('\n', '\n    ')
            github_comments += f"   {review.get('author', '')} ({review.get('role', '')}): {formatted_review}\n"
            
        return github_comments

if __name__ == "__main__":
    # test make_ground_truth_text with a sample commit_info
    owner = 'huggingface'
    repo_name = 'transformers'
    local_repo_path = Path(r'../huggingface_transformer_clone/transformers').absolute().resolve()
    from agentic_code_reviewer.environment_manager import get_or_prompt_github_token
    token = get_or_prompt_github_token()
    repo_evaluator = RepoEvaluator(
        owner=owner, 
        repo_name=repo_name, 
        local_repo_path=local_repo_path, 
        token=token
    )
    
    pr_number = 46419
    
    import pandas as pd
    df_path = Path(__file__).parent / owner / f"{repo_name}_evaluation_prs.csv"
                
    # results = RepoEvaluator.mine_evaluation_prs("huggingface", "transformers", max_files=10, min_maintainer_threads=2, target_count=0)
    # df = pd.DataFrame(results)
    
    df = pd.read_csv(df_path)
    df = df.sort_values(by=["authoritative_threads", "changed_files"], ascending=[False, True])
    df_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(df_path, index=False)
    print(f"Results saved to {df_path}")
    
    