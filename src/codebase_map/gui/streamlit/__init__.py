# src\codebase_map\gui\streamlit\__init__.py
import sys
import subprocess
from pathlib import Path
from importlib.resources import files

def launch_gui(repo_path: str | Path):
    repo_path = Path(repo_path).resolve()
    
    try:
        gui_path = files("codebase_map.gui.streamlit").joinpath("app.py")
    except Exception:
        gui_path = Path(__file__).parent / "app.py"

    # Launch Streamlit via subprocess with command-line arguments
    cmd = [
        "streamlit", "run",
        str(gui_path),
        "--server.headless=false",
        "--browser.gatherUsageStats=false",
        "--",               # <--- CRITICAL: Tells Streamlit to stop parsing arguments
        str(repo_path)      # <--- Your argument gets passed to sys.argv in app.py
    ]

    print(f"🚀 Launching GUI for: {repo_path}")
    subprocess.run(cmd)     # No env=env needed!