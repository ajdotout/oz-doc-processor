import os
from pathlib import Path
from dotenv import load_dotenv

# Auto-load .env at repo root
env_path = Path(__file__).resolve().parents[1] / ".env"
if env_path.exists():
    load_dotenv(env_path)  # do not override existing env 