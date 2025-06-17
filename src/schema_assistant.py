from schema_designer import SchemaDesigner
from langchain_core.prompts import ChatPromptTemplate
from llm_factory import LLMFactory
import re
from sqlalchemy.sql import text
from sqlalchemy import MetaData
from schema_history import SchemaHistoryManager
from sql_validator import SQLValidator

class SchemaAssistant:
    def __init__(self, db_url: str, schema_name: str, llm_provider: str = "gemini"):
        print("[SchemaAssistant] Initializing...")
        self.designer = SchemaDesigner(db_url)
        self.llm = LLMFactory.create_llm(llm_provider)
        self.history_manager = SchemaHistoryManager(schema_name)
        self.sql_validator = SQLValidator()
        print("[SchemaAssistant] Initialization complete")
    
    def process_command(self, command: str) -> dict:
        """Process a natural language command for schema manipulation"""
        try:
            # Add user command to history
            self.history_manager.add_entry("user", command)
            
            # Get current schema information
            schema_info = self._get_schema_info()
            
            # Create prompt for schema manipulation
            prompt = ChatPromptTemplate.from_messages([
                ("system", f"""You are a database schema expert. Convert the user's natural language request into 
                MySQL DDL statements.Thnk bigger and anticipate what all tables and users will need. Return ONLY the SQL statements without any explanation or formatting.

                Current Database Schema:
                {schema_info}
                
                Rules:
                GIVE SQL FOR MYSQL. FOLLOW THE EXAMPLE OUTPUTS.
                1. Always design using entity relationship modeling. Try to have seperarte tables for each entity and relationships. 
                2. Only reference tables and columns that exist in the schema. Dont give excessive columns or tables. Be mindful but take into account what the user wants and entity relationships.
                3. For new tables or columns, use appropriate data types and constraints. Use on delete cascade for foreign keys.

                4. For ALTER TABLE, ensure the table exists before suggesting modifications
                5. For foreign keys, ensure referenced tables and columns exist
                6. Use exact column names as shown in the schema
                8. Each table and column must have a comment
                9. Use MySQL comment syntax:
                   - Table: CREATE TABLE name (...) COMMENT = 'description';
                   - Column: column_name type COMMENT 'description'
                10. Return INVALID_REQUEST if the operation cannot be performed
                11. Each statement must end with a semicolon
                12. No markdown, no explanations, just SQL
                13. While truncating, always take care of foreign keys. Disable foreign keys, truncate, then enable.
                14. When creating new tables and columns, take into account the foreign keys and relationships so that ERD is maintained.

                Example Outputs:
                

                1. CREATE TABLE Persons (
                    id INT PRIMARY KEY AUTO_INCREMENT COMMENT 'Unique identifier',
                    name VARCHAR(255) NOT NULL COMMENT 'Person name'
                ) COMMENT = 'Stores person information';
                
                2. CREATE TABLE staff_area_assignments (
    assignment_id INTEGER NOT NULL PRIMARY KEY COMMENT 'Unique identifier for staff area assignment',
    staff_id INTEGER COMMENT 'Maintenance staff ID',
    area_id INTEGER COMMENT 'Hospital area ID',
    FOREIGN KEY (staff_id) REFERENCES hospital_maintenance_staff(staff_id) ON DELETE CASCADE,
    FOREIGN KEY (area_id) REFERENCES hospital_areas(area_id) ON DELETE CASCADE
) COMMENT = 'Stores assignments of maintenance staff to hospital areas';
                
                3. ALTER TABLE Persons ADD COLUMN email VARCHAR(255) NOT NULL COMMENT 'Person email';
                
                4. DROP TABLE Persons;
                
                5. COMMENT ON TABLE Persons IS 'Stores person information';
                
                5. RENAME TABLE Persons TO People;
                
                6. TRUNCATE TABLE Persons;
                
                """),
                ("human", "{command}")
            ])
            
            # Get SQL from LLM
            chain = prompt | self.llm
            sql_result = chain.invoke({"command": command})
            
            # Extract content from AIMessage
            sql_content = sql_result.content if hasattr(sql_result, 'content') else str(sql_result)
            if sql_content.strip() == 'INVALID_REQUEST':
                return {
                    "success": False,
                    "error": "Cannot perform this operation with the current schema"
                }
            
            print(f"[SchemaAssistant] Generated SQL:\n{sql_content}")
            
            # Extract SQL (remove any markdown formatting if present)
            sql_query = self._extract_sql(sql_content)
            print(f"[SchemaAssistant] Cleaned SQL:\n{sql_query}")
            
            # Validate and execute the SQL
            if self._validate_sql(sql_query):
                print("[SchemaAssistant] SQL validation passed")
                result = self._execute_sql(sql_query)
                print(f"[SchemaAssistant] Execution result: {result}")
                
                # Add SQL to result dictionary
                if result["success"]:
                    result["sql"] = sql_query
                    self.history_manager.add_entry(
                        "assistant",
                        result["message"],
                        sql_query  # Pass the SQL query here
                    )
                else:
                    self.history_manager.add_entry(
                        "assistant",
                        result["error"]
                    )
                
                return result
            else:
                print("[SchemaAssistant] SQL validation failed")
                return {
                    "success": False,
                    "error": "Invalid SQL generated",
                    "sql": sql_query
                }
                
        except Exception as e:
            error_msg = str(e)
            # Add error response to history
            self.history_manager.add_entry(
                "assistant",
                f"Error: {error_msg}"
            )
            return {
                "success": False,
                "error": error_msg
            }
    
    def _extract_sql(self, llm_response: str) -> str:
        """Extract SQL from LLM response, removing any markdown or explanations"""
        print(f"[SchemaAssistant] Extracting SQL from:\n{llm_response}")
        
        # Clean up the response
        sql = llm_response.strip()
        
        # Remove any markdown formatting
        if sql.startswith("```") and sql.endswith("```"):
            sql = sql[3:-3].strip()
            if sql.startswith("sql"):
                sql = sql[3:].strip()
        
        # Remove any line comments
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        
        # Remove any block comments
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        
        # Validate that it contains SQL-like statements
        sql_keywords = r"(CREATE|ALTER|DROP|TRUNCATE|DELETE|INSERT|UPDATE)\s+(?:TABLE|FROM)?|COMMENT\s+ON"
        if not re.search(sql_keywords, sql, re.IGNORECASE):
            print("[SchemaAssistant] No valid SQL found")
            return ""
        
        print("[SchemaAssistant] Extracted SQL statements")
        return sql
    
    def _validate_sql(self, sql: str) -> bool:
        """Validate that the SQL is safe to execute"""
        print(f"[SchemaAssistant] Validating SQL:\n{sql}")
        
        # Split into individual statements
        statements = [s.strip() for s in sql.split(';') if s.strip()]
        
        for statement in statements:
            # Skip empty statements
            if not statement:
                continue
            
            # Use SQLValidator with schema operation type
            is_valid, validation_message = self.sql_validator.validate(statement, operation_type="schema")
            if not is_valid:
                print(f"[SchemaAssistant] {validation_message}")
                return False
        
        return True
    
    def _execute_sql(self, sql: str) -> dict:
        """Execute SQL statement(s)"""
        try:
            # Remove comments and clean up SQL
            sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
            sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            
            results = []
            for statement in statements:
                if not statement:
                    continue
                    
                print(f"[SchemaAssistant] Executing statement: {statement}")
                try:
                    with self.designer.engine.begin() as conn:
                        conn.execute(text(statement))
                    results.append({
                        'success': True,
                        'message': f'Successfully executed: {statement}'
                    })
                except Exception as e:
                    results.append({
                        'success': False,
                        'error': f'Error executing statement: {str(e)}'
                    })
                    break
            
            # Return first error or last success
            for result in results:
                if not result['success']:
                    return result
            return results[-1] if results else {
                'success': False,
                'error': 'No valid SQL statements found'
            }
            
        except Exception as e:
            print(f"[SchemaAssistant] Error executing SQL: {str(e)}")
            return {
                'success': False,
                'error': f'Error executing SQL: {str(e)}'
            }

    def _handle_create_table(self, sql: str) -> dict:
        """Handle CREATE TABLE statement"""
        try:
            # Remove inline comments
            sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
            
            # Extract table name and columns
            table_name = re.search(r"CREATE TABLE (\w+)", sql, re.IGNORECASE).group(1)
            columns_str = re.search(r"\((.*)\)", sql, re.DOTALL).group(1)
            
            # Extract table comment if present
            table_comment = None
            comment_match = re.search(r"\)\s*COMMENT\s*=\s*'(.*?)'", sql, re.IGNORECASE)
            if comment_match:
                table_comment = comment_match.group(1)
            
            # Split into individual definitions
            definitions = [d.strip() for d in columns_str.split(',') if d.strip()]
            
            columns = []
            column_comments = {}  # Store column comments for later
            
            for definition in definitions:
                if definition.upper().startswith('FOREIGN KEY'):
                    # Handle foreign key constraints
                    fk_match = re.search(r"FOREIGN KEY\s*\((\w+)\)\s*REFERENCES\s*(\w+)\s*\((\w+)\)", definition, re.IGNORECASE)
                    if fk_match:
                        col_name = fk_match.group(1)
                        ref_table = fk_match.group(2)
                        ref_col = fk_match.group(3)
                        for col in columns:
                            if col['name'] == col_name:
                                col['foreign_key'] = {
                                    'is_fk': True,
                                    'references': f"{ref_table}.{ref_col}"
                                }
                elif definition.upper().startswith('PRIMARY KEY'):
                    # Handle table-level primary key
                    pk_match = re.search(r"PRIMARY KEY\s*\((.*?)\)", definition, re.IGNORECASE)
                    if pk_match:
                        pk_columns = [c.strip() for c in pk_match.group(1).split(',')]
                        for col in columns:
                            if col['name'] in pk_columns:
                                col['primary_key'] = True
                else:
                    # Regular column definition
                    # Extract comment if present
                    comment_match = re.search(r"COMMENT\s+'(.*?)'", definition, re.IGNORECASE)
                    if comment_match:
                        comment = comment_match.group(1)
                        # Remove comment from definition for parsing
                        definition = re.sub(r"COMMENT\s+'.*?'", "", definition, re.IGNORECASE).strip()
                    
                    parts = definition.split()
                    if len(parts) >= 2:
                        name = parts[0]
                        type_str = parts[1]
                        
                        column_info = {
                            'name': name,
                            'type': type_str,
                            'nullable': True,
                            'primary_key': False,
                            'foreign_key': {'is_fk': False}
                        }
                        
                        # Store comment if found
                        if comment_match:
                            column_comments[name] = comment_match.group(1)
                        
                        # Parse constraints
                        constraints = ' '.join(parts[2:]).upper()
                        if 'PRIMARY KEY' in constraints:
                            column_info['primary_key'] = True
                        if 'NOT NULL' in constraints:
                            column_info['nullable'] = False
                        if 'REFERENCES' in constraints:
                            ref_match = re.search(r"REFERENCES\s+(\w+)\s*\((\w+)\)", constraints, re.IGNORECASE)
                            if ref_match:
                                column_info['foreign_key'] = {
                                    'is_fk': True,
                                    'references': f"{ref_match.group(1)}.{ref_match.group(2)}"
                                }
                        
                        columns.append(column_info)
            
            # Create the table first
            result = self.designer.create_table(table_name, columns)
            if not result['success']:
                return result
            
            # Add table comment if present
            if table_comment:
                self.designer.set_table_comment(table_name, table_comment)
            
            # Add column comments
            for col_name, comment in column_comments.items():
                self.designer.set_column_comment(table_name, col_name, comment)
            
            return result
            
        except Exception as e:
            print(f"[SchemaAssistant] Error parsing CREATE TABLE: {str(e)}")
            return {
                'success': False,
                'error': f'Error parsing CREATE TABLE: {str(e)}'
            }

    def _handle_truncate_table(self, sql: str) -> dict:
        """Handle TRUNCATE TABLE statement"""
        try:
            table_name = re.search(r"TRUNCATE TABLE (\w+)", sql, re.IGNORECASE).group(1)
            return self.designer.truncate_table(table_name)
        except Exception as e:
            return {
                'success': False,
                'error': f'Error parsing TRUNCATE TABLE: {str(e)}'
            }

    def _handle_comment(self, sql: str) -> dict:
        """Handle COMMENT ON statements"""
        try:
            if 'COMMENT ON TABLE' in sql.upper():
                match = re.search(r"COMMENT ON TABLE (\w+) IS '(.*?)'", sql, re.IGNORECASE)
                table_name = match.group(1)
                comment = match.group(2)
                return self.designer.set_table_comment(table_name, comment)
            else:
                match = re.search(r"COMMENT ON COLUMN (\w+)\.(\w+) IS '(.*?)'", sql, re.IGNORECASE)
                table_name = match.group(1)
                column_name = match.group(2)
                comment = match.group(3)
                return self.designer.set_column_comment(table_name, column_name, comment)
        except Exception as e:
            return {
                'success': False,
                'error': f'Error parsing COMMENT statement: {str(e)}'
            }

    def _handle_rename_table(self, sql: str) -> dict:
        """Handle RENAME TABLE statement"""
        try:
            match = re.search(r"RENAME TABLE (\w+) TO (\w+)", sql, re.IGNORECASE)
            old_name = match.group(1)
            new_name = match.group(2)
            return self.designer.rename_table(old_name, new_name)
        except Exception as e:
            return {
                'success': False,
                'error': f'Error parsing RENAME TABLE: {str(e)}'
            }

    def _handle_alter_table(self, sql: str) -> dict:
        """Handle ALTER TABLE statement"""
        try:
            # Remove inline comments
            sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
            
            # Extract table name and operation
            match = re.search(r"ALTER TABLE (\w+)\s+(.*)", sql, re.IGNORECASE)
            if not match:
                return {
                    'success': False,
                    'error': 'Invalid ALTER TABLE syntax'
                }
            
            table_name = match.group(1)
            operation = match.group(2).strip()
            
            # Handle ADD COLUMN
            if re.search(r"ADD\s+COLUMN", operation, re.IGNORECASE):
                col_match = re.search(r"ADD\s+COLUMN\s+(\w+)\s+([^;]+)", operation, re.IGNORECASE)
                if col_match:
                    col_name = col_match.group(1)
                    col_def = col_match.group(2)
                    
                    # Parse column definition
                    parts = col_def.split()
                    col_type = parts[0]
                    
                    column_info = {
                        'name': col_name,
                        'type': col_type,
                        'nullable': True,
                        'primary_key': False,
                        'foreign_key': {'is_fk': False}
                    }
                    
                    # Parse constraints
                    constraints = ' '.join(parts[1:]).upper()
                    if 'PRIMARY KEY' in constraints:
                        column_info['primary_key'] = True
                    if 'NOT NULL' in constraints:
                        column_info['nullable'] = False
                    if 'REFERENCES' in constraints:
                        ref_match = re.search(r"REFERENCES\s+(\w+)\s*\((\w+)\)", constraints, re.IGNORECASE)
                        if ref_match:
                            column_info['foreign_key'] = {
                                'is_fk': True,
                                'references': f"{ref_match.group(1)}.{ref_match.group(2)}"
                            }
                    
                    return self.designer.add_column(table_name, column_info)
                    
            # Handle DROP COLUMN
            elif re.search(r"DROP\s+COLUMN", operation, re.IGNORECASE):
                col_match = re.search(r"DROP\s+COLUMN\s+(\w+)", operation, re.IGNORECASE)
                if col_match:
                    col_name = col_match.group(1)
                    return self.designer.drop_column(table_name, col_name)
                    
            # Handle MODIFY/ALTER COLUMN
            elif re.search(r"(MODIFY|ALTER)\s+COLUMN", operation, re.IGNORECASE):
                col_match = re.search(r"(?:MODIFY|ALTER)\s+COLUMN\s+(\w+)\s+([^;]+)", operation, re.IGNORECASE)
                if col_match:
                    col_name = col_match.group(1)
                    col_def = col_match.group(2)
                    
                    # Parse new column definition
                    parts = col_def.split()
                    col_type = parts[0]
                    
                    column_info = {
                        'name': col_name,
                        'type': col_type,
                        'nullable': True,
                        'primary_key': False,
                        'foreign_key': {'is_fk': False}
                    }
                    
                    # Parse constraints
                    constraints = ' '.join(parts[1:]).upper()
                    if 'PRIMARY KEY' in constraints:
                        column_info['primary_key'] = True
                    if 'NOT NULL' in constraints:
                        column_info['nullable'] = False
                    
                    return self.designer.modify_column(table_name, column_info)
            
            return {
                'success': False,
                'error': f'Unsupported ALTER TABLE operation: {operation}'
            }
            
        except Exception as e:
            print(f"[SchemaAssistant] Error parsing ALTER TABLE: {str(e)}")
            return {
                'success': False,
                'error': f'Error parsing ALTER TABLE: {str(e)}'
            }

    def _get_schema_info(self) -> str:
        """Get current schema information in a readable format"""
        metadata = MetaData()
        metadata.reflect(bind=self.designer.engine)
        
        schema_info = []
        for table in metadata.tables.values():
            # Add table info
            table_info = [f"Table: {table.name}"]
            if table.comment:
                table_info.append(f"Comment: {table.comment}")
            
            # Add column info
            columns = []
            for column in table.columns:
                col_info = f"  - {column.name} {column.type}"
                if not column.nullable:
                    col_info += " NOT NULL"
                if column.primary_key:
                    col_info += " PRIMARY KEY"
                if column.comment:
                    col_info += f" COMMENT '{column.comment}'"
                
                # Add foreign key info
                for fk in column.foreign_keys:
                    col_info += f" REFERENCES {fk.target_fullname}"
                
                columns.append(col_info)
            
            if columns:
                table_info.append("Columns:")
                table_info.extend(columns)
            
            schema_info.append("\n".join(table_info))
        
        return "\n\n".join(schema_info)

    def get_history(self):
        """Get schema modification history"""
        return self.history_manager.get_history()

    def clear_history(self):
        """Clear schema modification history"""
        self.history_manager.clear_history()

    def cleanup(self):
        """Clean up resources when schema is deleted"""
        return self.history_manager.delete_history_file()

    def _handle_delete(self, sql: str) -> dict:
        """Handle DELETE statement"""
        try:
            # Extract table name and where clause
            match = re.search(r"DELETE\s+FROM\s+(\w+)(?:\s+WHERE\s+(.+))?", sql, re.IGNORECASE)
            if not match:
                return {
                    'success': False,
                    'error': 'Invalid DELETE syntax'
                }
            
            table_name = match.group(1)
            where_clause = match.group(2) if match.group(2) else None
            
            # Execute the DELETE statement
            with self.designer.engine.begin() as conn:
                if where_clause:
                    conn.execute(text(f"DELETE FROM {table_name} WHERE {where_clause}"))
                else:
                    conn.execute(text(f"DELETE FROM {table_name}"))
                
            return {
                'success': True,
                'message': f'Successfully deleted records from {table_name}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error executing DELETE: {str(e)}'
            }