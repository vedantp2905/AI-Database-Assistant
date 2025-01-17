from datetime import datetime
import json
import os
from typing import Dict, List
import logging

class SchemaHistoryManager:
    def __init__(self, schema_name: str):
        self.schema_name = schema_name
        self.history_dir = "schema_history"
        self.history_file = f"{self.history_dir}/{schema_name}_history.json"
        self._ensure_history_dir()
        self._load_history()

    def _ensure_history_dir(self):
        """Ensure history directory exists"""
        os.makedirs(self.history_dir, exist_ok=True)

    def _load_history(self):
        """Load existing history or create new"""
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r') as f:
                self.history = json.load(f)
        else:
            self.history = []

    def _save_history(self):
        """Save history to file"""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)

    def add_entry(self, role: str, content: str, sql: str = None):
        """Add new entry to history"""
        if role == "assistant" and sql and sql.strip():
            # For assistant responses with SQL, store just the SQL
            entry = {
                "role": role,
                "content": "Successfully executed SQL",
                "sql": sql.strip(),
                "timestamp": datetime.now().isoformat()
            }
        else:
            # For user messages or non-SQL responses
            entry = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
        
        self.history.append(entry)
        self._save_history()

    def get_history(self) -> List[Dict]:
        """Get all history entries"""
        return self.history

    def clear_history(self):
        """Clear history"""
        self.history = []
        self._save_history()

    def delete_history_file(self):
        """Delete the history file if it exists"""
        try:
            if os.path.exists(self.history_file):
                os.remove(self.history_file)
                return True
        except Exception as e:
            logging.error(f"Failed to delete history file: {e}")
        return False 