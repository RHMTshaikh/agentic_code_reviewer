from pathlib import Path

# 1. __file__ is the absolute path to this specific paths.py file
# 2. .resolve() ensures all symlinks are resolved to the real path
# 3. .parent moves up one level to the 'my_package' directory
PACKAGE_ROOT = Path(__file__).resolve().parent

CWD = Path.cwd()

# 4. Append your specific file name to the root directory
MODELS_REGISTRY_FILE_PATH = PACKAGE_ROOT / "models_registry.json"

EVALUATIONS_DIR_PATH = CWD / "evaluations"

EVALUATION_SCORES_FILE_PATH = EVALUATIONS_DIR_PATH / "evaluation_scores.json"

REPORTS_DIR_PATH = CWD / "reports"