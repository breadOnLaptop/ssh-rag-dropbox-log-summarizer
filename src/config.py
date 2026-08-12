import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = os.getenv("LOG_AGENT_BASE_DIR", "/opt/log_agent")
DROP_ZONES_DIR = os.getenv("LOG_AGENT_DROP_ZONES_DIR", os.path.join(BASE_DIR, "drop_zones"))
RAG_DB_PATH = os.getenv("RAG_DB_PATH", os.path.join(BASE_DIR, "rag_context.db"))

API_URL = os.getenv("LOG_AGENT_API_URL", "http://10.221.51.121:11434/api/chat")
MODEL = os.getenv("LOG_AGENT_MODEL", "gemma4:12b")
MAX_FILE_SIZE = int(os.getenv("LOG_AGENT_MAX_FILE_SIZE", 1 * 1024 * 1024))
