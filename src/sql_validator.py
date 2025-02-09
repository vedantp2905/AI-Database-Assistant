import sqlparse
from sqlparse.sql import Statement, Token
from sqlparse.tokens import Keyword, DML, DDL
from typing import Tuple

class SQLValidator:
    def __init__(self):
        # Allow all common DDL operations
        self.allowed_operations = {
            'SELECT', 'CREATE', 'ALTER', 'DROP', 'TRUNCATE', 
            'RENAME', 'COMMENT', 'INSERT', 'UPDATE', 'DELETE', 
            'GRANT', 'REVOKE', 'SHUTDOWN', 'KILL', 'RELOAD',
            'FLUSH', 'RESET', 'PURGE', 'CHANGE MASTER'
        }
    
    def validate(self, query: str) -> Tuple[bool, str]:
        """
        Validates SQL query for safety and correctness
        Returns: (is_valid, error_message)
        """
        try:
            # Parse the SQL query
            parsed = sqlparse.parse(query)
            if not parsed:
                return False, "Empty or invalid SQL query"
            
            # Get the first statement
            statement: Statement = parsed[0]
            
            # Check if multiple statements
            if len(parsed) > 1:
                return False, "Multiple SQL statements are not allowed"
            
            # Get the first token (should be the operation type)
            first_token = None
            for token in statement.tokens:
                if not token.is_whitespace:
                    first_token = token
                    break
            
            if not first_token:
                return False, "No valid SQL operation found"
            
            # Check if it's a SELECT query
            if first_token.ttype is DML and first_token.value.upper() != 'SELECT':
                return False, "Only SELECT operations are allowed"
            
            # Validate basic syntax
            if not statement.is_group:

                return False, "Invalid SQL syntax"
            
            return True, "Valid query"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}" 