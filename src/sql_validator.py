import sqlparse
from sqlparse.sql import Statement, Token
from sqlparse.tokens import Keyword, DML, DDL
from typing import Tuple

class SQLValidator:
    def __init__(self):
        # Define allowed operations by category
        self.allowed_query_operations = {'SELECT'}
        self.allowed_schema_operations = {
            'CREATE', 'ALTER', 'DROP', 'TRUNCATE', 
            'RENAME', 'COMMENT'
        }
        self.allowed_data_operations = {
            'INSERT', 'UPDATE', 'DELETE'
        }
    
    def validate(self, query: str, operation_type="query") -> Tuple[bool, str]:
        """
        Validates SQL query for safety and correctness
        
        Args:
            query: The SQL query to validate
            operation_type: Type of operation to validate for
                            "query" - Only allow SELECT
                            "schema" - Allow schema modification operations
                            "data" - Allow data modification operations
                            "all" - Allow all operations
        
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
            
            # Get the operation type
            operation = first_token.value.upper()
            
            # Validate based on operation type
            if operation_type == "query":
                if operation != 'SELECT':
                    return False, "Only SELECT operations are allowed for queries"
            elif operation_type == "schema":
                if operation not in self.allowed_schema_operations:
                    return False, f"Operation {operation} not allowed for schema modifications"
            elif operation_type == "data":
                if operation not in self.allowed_data_operations:
                    return False, f"Operation {operation} not allowed for data modifications"
            elif operation_type == "all":
                # Allow all operations
                pass
            else:
                return False, f"Unknown operation type: {operation_type}"
            
            # Validate basic syntax
            if not statement.is_group:
                return False, "Invalid SQL syntax"
            
            return True, "Valid query"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}" 