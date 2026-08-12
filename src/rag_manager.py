import sqlite3
import os
from src.error_handler import handle_error, logger

class RAGContextManager:
    """Manages the Retrieval-Augmented Generation (RAG) context storage and retrieval using SQLite FTS5."""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS log_knowledge 
                    USING fts5(error_snippet, root_cause, fix);
                """)
        except Exception as e:
            handle_error(e, "initializing RAG database")

    def store_knowledge(self, error_snippet, root_cause, fix):
        """Stores analysis into the RAG context for future learning."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO log_knowledge (error_snippet, root_cause, fix) VALUES (?, ?, ?)",
                    (error_snippet, root_cause, fix)
                )
        except Exception as e:
            handle_error(e, "storing RAG knowledge")

    def retrieve_context(self, log_content, limit=3):
        """Retrieves past analyses relevant to the current log content."""
        try:
            # Extract large words to use as a basic keyword search against the FTS table
            words = [w for w in log_content.split() if len(w) > 5][:8]
            if not words:
                return []
                
            query = " OR ".join(words)
            # Sanitize query for SQLite FTS5
            safe_query = query.replace("'", "").replace('"', "")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT error_snippet, root_cause, fix FROM log_knowledge WHERE log_knowledge MATCH ? LIMIT ?",
                    (safe_query, limit)
                )
                return cursor.fetchall()
        except Exception as e:
            # Silently fallback to no context if query fails
            logger.debug(f"RAG Retrieval failed for query: {e}")
            return []
