import os
import time
import json
import queue
import logging
import threading
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- Configuration (using env vars for testability) ---
BASE_DIR = os.getenv("LOG_AGENT_BASE_DIR", "/opt/log_agent")
CONFIG_PATH = os.getenv("LOG_AGENT_CONFIG_PATH", os.path.join(BASE_DIR, "config", "user_keys.json"))
DROP_ZONES_DIR = os.getenv("LOG_AGENT_DROP_ZONES_DIR", os.path.join(BASE_DIR, "drop_zones"))

# Open WebUI API endpoints
API_URL = os.getenv("LOG_AGENT_API_URL", "http://localhost:3000/api/chat/completions")
MODEL = os.getenv("LOG_AGENT_MODEL", "gemma-4")

# Max context limit to prevent OOM crashes
MAX_FILE_SIZE = int(os.getenv("LOG_AGENT_MAX_FILE_SIZE", 1 * 1024 * 1024))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
task_queue = queue.Queue()


def get_user_token(username):
    try:
        with open(CONFIG_PATH, 'r') as f:
            keys = json.load(f)
            return keys.get(username)
    except FileNotFoundError:
        logging.error(f"Config file not found: {CONFIG_PATH}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Config file is not valid JSON: {CONFIG_PATH}")
        return None
    except Exception as e:
        logging.error(f"Error reading config: {e}")
        return None


def process_log(file_path):
    # Determine which user uploaded the file based on the directory structure
    # Expected: DROP_ZONES_DIR/<username>/logs_in/filename.ext
    abs_drop_zone = os.path.abspath(DROP_ZONES_DIR)
    abs_file_path = os.path.abspath(file_path)
    
    if not abs_file_path.startswith(abs_drop_zone):
        logging.error(f"File path is outside of drop zones: {file_path}")
        return

    rel_path = os.path.relpath(abs_file_path, abs_drop_zone)
    parts = rel_path.split(os.sep)
    
    if len(parts) < 3:
        logging.error(f"Invalid file path structure within drop zone: {file_path}")
        return
        
    username = parts[0]
    folder = parts[1]
    
    if folder != "logs_in":
        # We only process files in logs_in
        return

    token = get_user_token(username)
    if not token:
        logging.error(f"Missing Open WebUI API token for user: {username}")
        return

    if not os.path.exists(file_path):
        logging.error(f"File no longer exists: {file_path}")
        return

    # Edge Case: Handle massive log files by tailing the end
    size = os.path.getsize(file_path)
    if size > MAX_FILE_SIZE:
        logging.warning(f"File {file_path} is {size} bytes. Truncating to the latest {MAX_FILE_SIZE} bytes.")
        with open(file_path, 'rb') as f:
            f.seek(-MAX_FILE_SIZE, os.SEEK_END)
            log_content = f.read().decode('utf-8', errors='ignore')
    else:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            log_content = f.read()

    filename = os.path.basename(file_path)
    
    # Structure the prompt for the model
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a senior DevOps engineer. Analyze the provided log file. Generate a strict Markdown (.md) report containing: 1. Executive Summary, 2. Root Cause Analysis (with specific error codes), 3. Recommended Fixes."
            },
            {
                "role": "user",
                "content": f"Log filename: {filename}\n\n{log_content}"
            }
        ],
        "stream": False
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    logging.info(f"Triggering inference for {username} on file {filename}...")
    try:
        # Timeout set high (120s) as large context processing can take time
        response = requests.post(API_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        
        reply = response.json().get("choices", [{}])[0].get("message", {}).get("content", "Error parsing output.")
        
        # Save output strictly as .md in the user's outbox
        out_name = f"{os.path.splitext(filename)[0]}_summary.md"
        out_path = os.path.join(DROP_ZONES_DIR, username, "reports_out", out_name)
        
        # Ensure the reports_out directory exists
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(reply)
            
        logging.info(f"Report complete: {out_path}")
        
    except requests.exceptions.RequestException as e:
        logging.error(f"API Request Error for {filename}: {e}")
    except Exception as e:
        logging.error(f"Unexpected Error processing {filename}: {e}")


def worker():
    # Processes one file at a time from the queue to prevent API rate limit / Model OOM
    while True:
        file_path = task_queue.get()
        if file_path is None: 
            break
        try:
            process_log(file_path)
        except Exception as e:
            logging.error(f"Worker failure: {e}")
        finally:
            task_queue.task_done()


class LogDropHandler(FileSystemEventHandler):
    def on_closed(self, event):
        # on_closed ensures SCP has entirely finished writing the file
        if not event.is_directory and "logs_in" in event.src_path:
            filename = os.path.basename(event.src_path)
            # Edge Case: Ignore hidden temp files generated by SCP or macOS
            if filename.startswith('.') or filename.endswith('.tmp'):
                return
            
            logging.info(f"File completely uploaded: {event.src_path}")
            task_queue.put(event.src_path)


def start_daemon():
    logging.info("Initializing Log Agent Watcher Daemon...")
    
    # Spin up the background processing thread
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    
    # Attach Watchdog to recursively monitor all user folders
    observer = Observer()
    observer.schedule(LogDropHandler(), DROP_ZONES_DIR, recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping Log Agent Watcher Daemon...")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_daemon()
