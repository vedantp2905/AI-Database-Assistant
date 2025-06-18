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
        
        # MySQL-specific disallowed functions/keywords
        self.mysql_disallowed = {
            'CONNECT_BY', 'ROWNUM', 'ROWID', 'FETCH', 'WITH RECURSIVE',  
            'PIVOT', 'UNPIVOT', 'MERGE'
        }
    
    def validate(self, query: str, operation_type="query", dialect="mysql") -> Tuple[bool, str]:
        """
        Validates SQL query for safety and correctness
        
        Args:
            query: The SQL query to validate
            operation_type: Type of operation to validate for
                            "query" - Only allow SELECT
                            "schema" - Allow schema modification operations
                            "data" - Allow data modification operations
                            "all" - Allow all operations
            dialect: SQL dialect to validate against (currently only "mysql" is supported)
        
        Returns: (is_valid, error_message)
        """
        if dialect != "mysql":
            return False, "Only MySQL dialect is supported"
            
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
            
            # MySQL-specific validation
            query_upper = query.upper()
            for disallowed in self.mysql_disallowed:
                if disallowed in query_upper:
                    return False, f"MySQL does not support '{disallowed}' syntax"
            
            return True, "Valid query"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
            
    def validate_mysql_functions(self, query: str) -> Tuple[bool, str]:
        """
        Validates that the query only uses MySQL-compatible functions
        
        Args:
            query: The SQL query to validate
            
        Returns: (is_valid, error_message)
        """
        # List of non-MySQL function patterns to check
        non_mysql_patterns = [
            ('||', 'String concatenation should use CONCAT() in MySQL'),
            ('TO_CHAR', 'Use DATE_FORMAT() instead of TO_CHAR() in MySQL'),
            ('NVL', 'Use IFNULL() instead of NVL() in MySQL'),
            ('DECODE', 'Use CASE WHEN instead of DECODE() in MySQL'),
            ('ROWNUM', 'Use LIMIT instead of ROWNUM in MySQL'),
            ('REGEXP_LIKE', 'Use REGEXP instead of REGEXP_LIKE in MySQL'),
            ('SYSDATE', 'Use NOW() or CURRENT_TIMESTAMP() instead of SYSDATE in MySQL')
        ]
        
        query_upper = query.upper()
        for pattern, message in non_mysql_patterns:
            if pattern in query_upper:
                return False, message
                
        return True, "Valid MySQL functions" 