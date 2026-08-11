import os
import json
import pytest
import responses
import tempfile
import shutil
from src.watcher import process_log

@pytest.fixture
def setup_env():
    # Create a temporary directory for tests
    temp_dir = tempfile.mkdtemp()
    
    # Override environment variables
    os.environ["LOG_AGENT_BASE_DIR"] = temp_dir
    os.environ["LOG_AGENT_CONFIG_PATH"] = os.path.join(temp_dir, "config", "user_keys.json")
    os.environ["LOG_AGENT_DROP_ZONES_DIR"] = os.path.join(temp_dir, "drop_zones")
    os.environ["LOG_AGENT_API_URL"] = "http://mockapi:3000/api/chat/completions"
    os.environ["LOG_AGENT_MAX_FILE_SIZE"] = str(1024) # 1KB for testing
    
    # Reload watcher config for test
    import src.watcher as watcher
    watcher.BASE_DIR = temp_dir
    watcher.CONFIG_PATH = os.path.join(temp_dir, "config", "user_keys.json")
    watcher.DROP_ZONES_DIR = os.path.join(temp_dir, "drop_zones")
    watcher.API_URL = "http://mockapi:3000/api/chat/completions"
    watcher.MAX_FILE_SIZE = 1024
    
    # Setup directories
    os.makedirs(os.path.join(temp_dir, "config"))
    os.makedirs(os.path.join(temp_dir, "drop_zones", "alice", "logs_in"))
    os.makedirs(os.path.join(temp_dir, "drop_zones", "alice", "reports_out"))
    
    # Setup mock config
    with open(watcher.CONFIG_PATH, 'w') as f:
        json.dump({"alice": "sk-mock-token"}, f)
        
    yield temp_dir, watcher
    
    # Cleanup
    shutil.rmtree(temp_dir)

@responses.activate
def test_process_log_success(setup_env):
    temp_dir, watcher = setup_env
    
    # Create a test log file
    log_path = os.path.join(temp_dir, "drop_zones", "alice", "logs_in", "error.log")
    with open(log_path, 'w') as f:
        f.write("test log content")
        
    # Mock the API response
    responses.add(
        responses.POST,
        "http://mockapi:3000/api/chat/completions",
        json={
            "choices": [
                {
                    "message": {
                        "content": "# Test Summary\nAll good."
                    }
                }
            ]
        },
        status=200
    )
    
    # Run the function
    watcher.process_log(log_path)
    
    # Check if report was generated
    report_path = os.path.join(temp_dir, "drop_zones", "alice", "reports_out", "error_summary.md")
    assert os.path.exists(report_path)
    with open(report_path, 'r') as f:
        content = f.read()
        assert content == "# Test Summary\nAll good."

@responses.activate
def test_process_log_file_truncation(setup_env):
    temp_dir, watcher = setup_env
    
    # Create a large test log file (larger than 1KB)
    log_path = os.path.join(temp_dir, "drop_zones", "alice", "logs_in", "large.log")
    large_content = "A" * 2000
    with open(log_path, 'w') as f:
        f.write(large_content)
        
    # Mock the API response
    responses.add(
        responses.POST,
        "http://mockapi:3000/api/chat/completions",
        json={
            "choices": [{"message": {"content": "Truncated."}}]
        },
        status=200
    )
    
    watcher.process_log(log_path)
    
    # Verify the API was called with truncated content
    assert len(responses.calls) == 1
    req_body = json.loads(responses.calls[0].request.body)
    user_msg = req_body["messages"][1]["content"]
    assert "Log filename: large.log" in user_msg
    # Content should be exactly 1024 A's
    assert "A" * 1024 in user_msg
    assert len(user_msg) == len("Log filename: large.log\n\n") + 1024
    
def test_process_log_missing_token(setup_env, caplog):
    temp_dir, watcher = setup_env
    
    # Create an unregistered user
    os.makedirs(os.path.join(temp_dir, "drop_zones", "bob", "logs_in"))
    log_path = os.path.join(temp_dir, "drop_zones", "bob", "logs_in", "error.log")
    with open(log_path, 'w') as f:
        f.write("test log")
        
    watcher.process_log(log_path)
    
    # The function should exit early and log an error
    assert "Missing Open WebUI API token for user: bob" in caplog.text
    report_path = os.path.join(temp_dir, "drop_zones", "bob", "reports_out", "error_summary.md")
    assert not os.path.exists(report_path)
    
def test_process_log_invalid_path(setup_env, caplog):
    temp_dir, watcher = setup_env
    
    # Create a file outside of the expected structure
    log_path = os.path.join(temp_dir, "drop_zones", "alice", "wrong_folder", "error.log")
    os.makedirs(os.path.dirname(log_path))
    with open(log_path, 'w') as f:
        f.write("test log")
        
    watcher.process_log(log_path)
    
    report_path = os.path.join(temp_dir, "drop_zones", "alice", "reports_out", "error_summary.md")
    assert not os.path.exists(report_path)
