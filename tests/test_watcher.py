import os
import pytest
import responses
import tempfile
import shutil
from src.watcher import process_log

@pytest.fixture
def setup_env():
    # Create a temporary directory for tests
    temp_dir = tempfile.mkdtemp()
    
    # Setup mock configuration in the environment
    os.environ["LOG_AGENT_BASE_DIR"] = temp_dir
    os.environ["LOG_AGENT_DROP_ZONES_DIR"] = os.path.join(temp_dir, "drop_zones")
    os.environ["RAG_DB_PATH"] = os.path.join(temp_dir, "rag_context.db")
    os.environ["LOG_AGENT_API_URL"] = "http://mockapi:8080/api/chat/completions"
    os.environ["LOG_AGENT_MAX_FILE_SIZE"] = str(1024)
    
    # Reload modules
    import src.config as config
    config.BASE_DIR = temp_dir
    config.DROP_ZONES_DIR = os.path.join(temp_dir, "drop_zones")
    config.RAG_DB_PATH = os.path.join(temp_dir, "rag_context.db")
    config.API_URL = "http://mockapi:8080/api/chat/completions"
    config.MAX_FILE_SIZE = 1024
    
    import src.watcher as watcher
    watcher.DROP_ZONES_DIR = config.DROP_ZONES_DIR
    watcher.API_URL = config.API_URL
    watcher.MAX_FILE_SIZE = config.MAX_FILE_SIZE
    
    # Re-initialize the test DB
    from src.rag_manager import RAGContextManager
    watcher.rag_db = RAGContextManager(config.RAG_DB_PATH)
    
    # Setup drop zones
    os.makedirs(os.path.join(temp_dir, "drop_zones", "alice", "logs_in"))
    os.makedirs(os.path.join(temp_dir, "drop_zones", "alice", "reports_out"))
    
    yield temp_dir, watcher
    
    # Cleanup
    shutil.rmtree(temp_dir)

@responses.activate
def test_process_log_success(setup_env):
    temp_dir, watcher = setup_env
    
    log_path = os.path.join(temp_dir, "drop_zones", "alice", "logs_in", "error.log")
    with open(log_path, 'w') as f:
        f.write("test log content")
        
    responses.add(
        responses.POST,
        "http://mockapi:8080/api/chat/completions",
        json={"choices": [{"message": {"content": "| Line | Root Cause | Fix |\n|---|---|---|"}}] },
        status=200
    )
    
    watcher.process_log(log_path)
    
    # The new script generates '_matrix.md' instead of '_summary.md'
    report_path = os.path.join(temp_dir, "drop_zones", "alice", "reports_out", "error_matrix.md")
    assert os.path.exists(report_path)
    with open(report_path, 'r') as f:
        content = f.read()
        assert "| Line |" in content

@responses.activate
def test_process_log_file_chunking(setup_env):
    temp_dir, watcher = setup_env
    
    log_path = os.path.join(temp_dir, "drop_zones", "alice", "logs_in", "large.log")
    large_content = "A" * 2500  # Will create 3 chunks (1024, 1024, 452)
    with open(log_path, 'w') as f:
        f.write(large_content)
        
    responses.add(
        responses.POST,
        "http://mockapi:8080/api/chat/completions",
        json={"choices": [{"message": {"content": "Chunk matrix."}}] },
        status=200
    )
    
    watcher.process_log(log_path)
    
    assert len(responses.calls) == 3
    
    report_path = os.path.join(temp_dir, "drop_zones", "alice", "reports_out", "large_matrix.md")
    assert os.path.exists(report_path)
    with open(report_path, 'r') as f:
        content = f.read()
        assert "# Matrix Analysis Report for large.log" in content

def test_process_log_invalid_path(setup_env):
    temp_dir, watcher = setup_env
    
    log_path = os.path.join(temp_dir, "drop_zones", "alice", "wrong_folder", "error.log")
    os.makedirs(os.path.dirname(log_path))
    with open(log_path, 'w') as f:
        f.write("test log")
        
    watcher.process_log(log_path)
    
    report_path = os.path.join(temp_dir, "drop_zones", "alice", "reports_out", "error_matrix.md")
    assert not os.path.exists(report_path)
