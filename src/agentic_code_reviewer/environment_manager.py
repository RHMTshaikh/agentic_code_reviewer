import os
import getpass
from pathlib import Path
from dotenv import load_dotenv, set_key

# Target the .env file at the root of the project
ENV_FILE = Path(".env")

def get_or_prompt_api_key(key_name: str):
    """
    Loads existing keys via python-dotenv. If missing, prompts the user
    and uses the library to safely write the key to the .env file.
    """
    # 1. Automatically load anything currently inside the .env file into memory
    load_dotenv(dotenv_path=ENV_FILE)

    # 2. Check if the key is now available (either from OS or the .env we just loaded)
    existing_key = os.getenv(key_name)
    if existing_key:
        print(f"✅ Key for {key_name} is already available.")
        return existing_key

    # 3. First time user: Prompt for the key
    print("\n" + "="*50)
    print("🤖 Agentic Code Reviewer Setup")
    print("="*50)
    print("Welcome! Let's securely configure your local environment.")
    
    new_key = getpass.getpass(f"Enter your {key_name} API Key (input hidden): ").strip()
    
    if not new_key:
        raise ValueError(f"CRITICAL: You must provide an API key to run this {key_name}.")
    
    # 4. Use python-dotenv to safely write the key
    # If .env doesn't exist, it creates it. If the key exists, it cleanly overwrites it.
    # We must cast ENV_FILE to a string because set_key expects a string path.
    set_environment_key(key_name, new_key)
    
    print(f"✅ Key saved securely to {ENV_FILE.absolute()}")
    print("You won't be asked for this again in this project folder.\n")
    
    return new_key

def get_or_prompt_github_token():
    """
    Loads existing GitHub token via python-dotenv. If missing, prompts the user
    and uses the library to safely write the token to the .env file.
    """
    # 1. Automatically load anything currently inside the .env file into memory
    load_dotenv(dotenv_path=ENV_FILE)

    # 2. Check if the token is now available (either from OS or the .env we just loaded)
    existing_token = os.getenv("GITHUB_TOKEN")
    if existing_token:
        print(f"✅ GitHub token is already available.")
        return existing_token

    # 3. First time user: Prompt for the token
    print("\n" + "="*50)
    print("🤖 Agentic Code Reviewer Setup")
    print("="*50)
    print("Welcome! Let's securely configure your local environment.")
    
    new_token = getpass.getpass(f"Enter your GitHub Personal Access Token (input hidden): ").strip()
    
    if not new_token:
        raise ValueError(f"CRITICAL: You must provide a GitHub Personal Access Token to run this tool.")
    
    # 4. Use python-dotenv to safely write the token
    set_environment_key("GITHUB_TOKEN", new_token)
    
    print(f"✅ GitHub token saved securely to {ENV_FILE.absolute()}")
    print("You won't be asked for this again in this project folder.\n")
    
    return new_token

def set_environment_key(key_name: str, value: str):
    """
    Sets a key in the .env file and updates the current environment.
    """
    # Use python-dotenv to safely write the key
    set_key(
        dotenv_path=str(ENV_FILE), 
        key_to_set=key_name, 
        value_to_set=value
    )
    
    # Inject it into active RAM for the current script execution
    os.environ[key_name] = value
    