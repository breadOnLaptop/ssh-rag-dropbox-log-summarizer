import os
import time
import queue
import threading
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from src.config import BASE_DIR, DROP_ZONES_DIR, RAG_DB_PATH, API_URL, MODEL, MAX_FILE_SIZE
from src.error_handler import logger, handle_error
from src.rag_manager import RAGContextManager
from src.prompt_manager import PromptManager

task_queue = queue.Queue()
rag_db = RAGContextManager(RAG_DB_PATH)

def process_log(file_path):
    abs_drop_zone = os.path.abspath(DROP_ZONES_DIR)
    abs_file_path = os.path.abspath(file_path)
    
    if not abs_file_path.startswith(abs_drop_zone):
        logger.error(f"File path is outside of drop zones: {file_path}")
        return

    rel_path = os.path.relpath(abs_file_path, abs_drop_zone)
    parts = rel_path.split(os.sep)
    
    if len(parts) < 3 or parts[1] != "logs_in":
        return
        
    username = parts[0]

    if not os.path.exists(file_path):
        logger.error(f"File no longer exists: {file_path}")
        return

    filename = os.path.basename(file_path)
    size = os.path.getsize(file_path)
    
    chunks = []
    if size > MAX_FILE_SIZE:
        logger.warning(f"File {file_path} is {size} bytes. Splitting into chunks of ~{MAX_FILE_SIZE} characters.")
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            while True:
                chunk = f.read(MAX_FILE_SIZE)
                if not chunk:
                    break
                chunks.append(chunk)
    else:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            chunks.append(f.read())

    headers = {
        "Content-Type": "application/json"
    }

    all_replies = []
    
    for i, chunk_content in enumerate(chunks):
        logger.info(f"Triggering inference for {username} on file {filename} (Chunk {i+1}/{len(chunks)})...")
        
        # 1. Retrieve RAG Context
        context_rows = rag_db.retrieve_context(chunk_content)
        past_context = ""
        if context_rows:
            past_context = "\n".join([f"- Past Error: {r[0]} | Cause: {r[1]} | Fix: {r[2]}" for r in context_rows])
        
        is_chunk = len(chunks) > 1
        system_prompt = PromptManager.get_system_prompt(is_chunk=is_chunk, past_context=past_context)
        chunk_info = f"Chunk {i+1} of {len(chunks)}" if is_chunk else ""
        user_prompt = PromptManager.get_user_prompt(filename, chunk_content, chunk_info)
            
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False
        }

        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            
            reply = response.json().get("choices", [{}])[0].get("message", {}).get("content", "Error parsing output.")
            all_replies.append(reply)
            
            # 2. Store back in RAG Context
            # Storing the analysis back into RAG for future learning.
            # In a robust system, we would parse the markdown table to isolate root causes.
            rag_db.store_knowledge(chunk_content[:250], "Inferred from matrix analysis", "See generated matrix")
            
        except requests.exceptions.RequestException as e:
            handle_error(e, f"API Request Error for {filename} chunk {i+1}")
            all_replies.append(f"Error processing chunk {i+1}: {e}")
        except Exception as e:
            handle_error(e, f"Unexpected Error processing {filename} chunk {i+1}")
            all_replies.append(f"Unexpected Error processing chunk {i+1}: {e}")

    # Combine all chunk analyses if there are multiple chunks
    if len(chunks) > 1:
        final_report = f"# Matrix Analysis Report for {filename}\n\n"
        for i, reply in enumerate(all_replies):
            final_report += f"## Analysis for Chunk {i+1}\n{reply}\n\n---\n\n"
    else:
        final_report = all_replies[0]
        
    out_name = f"{os.path.splitext(filename)[0]}_matrix.md"
    out_path = os.path.join(DROP_ZONES_DIR, username, "reports_out", out_name)
    
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(final_report)
        
    logger.info(f"Report complete: {out_path}")

def worker():
    while True:
        file_path = task_queue.get()
        if file_path is None: 
            break
        try:
            process_log(file_path)
        except Exception as e:
            handle_error(e, "Worker failure")
        finally:
            task_queue.task_done()

class LogDropHandler(FileSystemEventHandler):
    def on_closed(self, event):
        if not event.is_directory and "logs_in" in event.src_path:
            filename = os.path.basename(event.src_path)
            if filename.startswith('.') or filename.endswith('.tmp'):
                return
            
            logger.info(f"File completely uploaded: {event.src_path}")
            task_queue.put(event.src_path)

def start_daemon():
    logger.info("Initializing Log Agent Watcher Daemon (RAG + Local Matrix Analysis)...")
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    
    observer = Observer()
    observer.schedule(LogDropHandler(), DROP_ZONES_DIR, recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping Log Agent Watcher Daemon...")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_daemon()
