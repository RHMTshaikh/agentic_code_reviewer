# src\codebase_map\git_utility.py
import subprocess
import re
from pathlib import Path

def _get_git_diff(project_path: Path) -> str:
    if not (project_path / ".git").exists():
        print(f"⚠️ The directory '{project_path}' is not a Git repository. Please initialize a Git repository or provide a valid path.")
        return ""
    
    git_command = "git diff --cached -U0 --function-context"
    # If any classes or methods are modified whole class will be considered as modified.
    # This is because the git diff command will show the entire class if any method within it is modified.
    # 1. Run the git command and capture the output
    result = subprocess.run(
        git_command.split(), 
        cwd=project_path,
        stdout=subprocess.PIPE,  # Capture stdout to get the diff output
        stderr=subprocess.PIPE,  # Capture stderr to handle errors
        text=True,         # This ensures the output is captured as a string rather than bytes
        encoding="utf-8",  # THE FIX: Force UTF-8 decoding
        errors="replace",  # SAFETY NET: Replace corrupted bytes with '?' instead of crashing
        check=True         # This forces Python to raise an exception if Git fails
    )
    # print error if any
    if result.stderr:
        print(f"⚠️ Git command error: {result.stderr.strip()}")
    return result.stdout
    
def _extract_modified_fqns(git_diff_text: str) -> list[str]:
    """
    Crawls a git diff output (generated with -U0 --function-context) 
    and returns a list of modified FQNs, strictly excluding module-level changes
    and entirely deleted nodes.
    """
    modified_nodes = set()
    current_module = None
    
    # Stores tuples of (indentation_level, scope_name)
    scope_stack = [] 

    # THE FIX: Removed '-' from the regex. We only want to match additions or context.
    definition_pattern = re.compile(r'^(?:[+ ])([ \t]*)(?:async\s+)?(?:class|def)\s+([a-zA-Z0-9_]+)')

    for line in git_diff_text.splitlines():
        # 1. Detect File Changes and update the Root Module FQN
        if line.startswith('+++ '):
            file_path = line[4:]
            if file_path.startswith('b/'):
                file_path = file_path[2:]
            
            if not file_path.endswith('.py'):
                current_module = None
                continue
            
            current_module = file_path[:-3].replace('/', '.')
            scope_stack = []
            continue
            
        if not current_module:
            continue

        # 2. Skip git metadata headers AND completely ignore deleted lines
        # By ignoring '-', deleted functions cannot pollute our scope stack.
        if line.startswith('@@') or line.startswith('index ') or line.startswith('-'):
            continue

        # 3. Process Context (' ') and Added ('+') Lines
        if line.startswith('+') or line.startswith(' '):
            code_line = line[1:]
            stripped = code_line.strip()
            
            # Ignore comments AND multi-line closures like ") -> Future:"
            if stripped and not stripped.startswith(('#', ')', ']', '}')):
                indent = len(code_line) - len(code_line.lstrip())
                
                # Pop scopes at the same or shallower indentation level
                while scope_stack and scope_stack[-1][0] >= indent:
                    scope_stack.pop()

                # Push new scopes
                match = definition_pattern.match(line)
                if match:
                    name = match.group(2)
                    scope_stack.append((indent, name))

            # 4. Record Modifications
            if line.startswith('+'):
                if not stripped:
                    continue
                
                if not scope_stack:
                    continue
                
                scope_path = ".".join([name for _, name in scope_stack])
                fqn = f"{current_module}.{scope_path}"
                modified_nodes.add(fqn)

    return sorted(modified_nodes)

def get_staged_fqns(project_path: Path) -> list[str]:
    git_diff_text = _get_git_diff(project_path)
    if not git_diff_text:
        return []
    
    modified_fqns = _extract_modified_fqns(git_diff_text)
    return modified_fqns

if __name__ == "__main__":
    project_path = Path(r'../document_align').absolute().resolve()
    project_path = Path(r'../huggingface_transformer_clone/transformers').absolute().resolve()
    print(f"Analyzing staged changes in Git repository at: {project_path}")
    
    git_diff_text = _get_git_diff(project_path)
    
    with open("outputs/git_diff_output.txt", "w", encoding="utf-8") as f:
        f.write(git_diff_text)
    
    modified_fqns = _extract_modified_fqns(git_diff_text)
    print("\nModified FQNs:")
    for fqn in modified_fqns:
        print(fqn)
        
    