from sqlalchemy import (
    MetaData, Table, Column, Integer, String, ForeignKey, create_engine, inspect, text,
    BigInteger, SmallInteger, Text, Boolean, Float, Numeric, Date, DateTime, 
    Time, LargeBinary, JSON, UUID, BINARY
)
import graphviz
from typing import List, Dict
import json
import os
import re
from sqlalchemy import text

class SchemaDesigner:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = create_engine(db_url)
        self.metadata = MetaData()
        self.inspector = inspect(self.engine)
        self.tables = {}
        self.relationships = []
        
        # Load existing schema if database exists
        self._load_existing_schema()
    
    def _load_existing_schema(self):
        """Load existing database schema"""
        for table_name in self.inspector.get_table_names():
            columns = []
            pk_columns = self.inspector.get_pk_constraint(table_name)['constrained_columns']
            
            for column in self.inspector.get_columns(table_name):
                col_info = {
                    'name': column['name'],
                    'type': str(column['type']),
                    'nullable': column['nullable']
                }
                
                # Check if column is primary key
                if column['name'] in pk_columns:
                    col_info['primary_key'] = True
                
                # Check for foreign keys
                for fk in self.inspector.get_foreign_keys(table_name):
                    if column['name'] in fk['constrained_columns']:
                        col_info['foreign_key'] = f"{fk['referred_table']}.{fk['referred_columns'][0]}"
                        # Store relationship
                        self.relationships.append({
                            'from': table_name,
                            'to': fk['referred_table'],
                            'type': '1:N'
                        })
                
                columns.append(col_info)
            
            # Create table object
            self.tables[table_name] = {
                'name': table_name,
                'columns': columns
            }

    def create_table(self, table_name: str, columns: List[Dict], primary_key: str = None):
        """Create a new table with specified columns"""
        print(f"\n[SchemaDesigner] Creating table: {table_name}")
        print(f"[SchemaDesigner] Columns: {json.dumps(columns, indent=2)}")
        
        try:
            cols = []
            for col in columns:
                print(f"[SchemaDesigner] Processing column: {col['name']}")
                
                # Get SQL type
                type_name = col['type'].lower()
                sql_type = self._get_sql_type(type_name)
                print(f"[SchemaDesigner] Mapped type {type_name} to {sql_type}")
                
                # Create column with constraints
                column = Column(
                    col['name'],
                    sql_type,
                    primary_key=col.get('primary_key', False),
                    nullable=col.get('nullable', True)
                )
                cols.append(column)
                print(f"[SchemaDesigner] Added column: {column}")
            
            # Create table in database
            print("[SchemaDesigner] Creating table in database...")
            table = Table(table_name, self.metadata, *cols)
            
            # Create the table immediately
            with self.engine.begin() as conn:
                table.create(conn, checkfirst=True)
            
            # Store table reference
            self.tables[table_name] = table
            print(f"[SchemaDesigner] Table {table_name} created successfully")
            
            return {
                "success": True,
                "message": f"Table {table_name} created successfully"
            }
            
        except Exception as e:
            print(f"[SchemaDesigner] Error creating table: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def drop_table(self, table_name: str):
        """Drop a table from the database"""
        try:
            with self.engine.begin() as conn:
                if table_name in self.tables:
                    self.tables[table_name].drop(conn)
                    del self.tables[table_name]
                    # Remove related relationships
                    self.relationships = [r for r in self.relationships 
                                        if r['from'] != table_name and r['to'] != table_name]
                    return {
                        "success": True,
                        "message": f"Table {table_name} dropped successfully"
                    }
                return {
                    "success": False,
                    "error": f"Table {table_name} does not exist"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_sql_type(self, type_name: str):
        """Convert common type names to SQLAlchemy types"""
        # Extract type and length if present
        match = re.match(r'(\w+)(?:\((\d+)\))?', type_name)
        if not match:
            return String(255)  # Default fallback
        
        base_type, length = match.groups()
        length = int(length) if length else None
        
        # Comprehensive type mapping
        type_map = {
            'serial': Integer,
            'int': Integer,
            'integer': Integer,
            'bigint': BigInteger,
            'smallint': SmallInteger,
            'varchar': lambda l: String(length=l if l else 255),
            'char': lambda l: String(length=l if l else 1),
            'text': Text,
            'boolean': Boolean,
            'bool': Boolean,
            'float': Float,
            'double': Float(precision=53),
            'decimal': Numeric,
            'date': Date,
            'datetime': DateTime,
            'timestamp': DateTime,
            'time': Time,
            'binary': BINARY,
            'blob': LargeBinary,
            'json': JSON,
            'uuid': UUID
        }
        
        base_type = base_type.lower()
        type_constructor = type_map.get(base_type)
        
        if type_constructor is None:
            print(f"[SchemaDesigner] Unknown type {base_type}, defaulting to VARCHAR(255)")
            return String(255)
        
        if callable(type_constructor) and length is not None:
            return type_constructor(length)
        elif callable(type_constructor):
            return type_constructor()
        else:
            return type_constructor
    
    def visualize_schema(self, output_path: str = "schema"):
        """Generate schema visualization using GraphViz"""
        dot = graphviz.Digraph(comment='Database Schema')
        dot.attr(rankdir='LR')
        
        # Add tables as nodes
        for table_name, table in self.tables.items():
            # Create HTML-like label for table
            label = f'''<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
                <TR><TD PORT="header" BGCOLOR="#4CAF50"><B>{table_name}</B></TD></TR>'''
            
            # Add columns
            for column in table.columns:
                pk_marker = "🔑 " if column.primary_key else ""
                fk_marker = "🔗 " if column.foreign_keys else ""
                label += f'<TR><TD PORT="{column.name}">{pk_marker}{fk_marker}{column.name}: {column.type}</TD></TR>'
            
            label += '</TABLE>>'
            dot.node(table_name, label=label, shape='none')
        
        # Add relationships as edges
        for rel in self.relationships:
            dot.edge(f"{rel['from']}", f"{rel['to']}", 
                    arrowhead='crow',
                    arrowtail='none')
        
        # Save visualization
        dot.render(output_path, format='png', cleanup=True)
        return f"{output_path}.png"
    
    def apply_schema(self):
        """Apply the schema to the database"""
        self.metadata.create_all(self.engine)
    
    def save_schema(self, filepath: str):
        """Save schema definition to JSON file"""
        schema_def = {
            'tables': {},
            'relationships': self.relationships
        }
        
        for table_name, table in self.tables.items():
            schema_def['tables'][table_name] = {
                'columns': [
                    {
                        'name': col.name,
                        'type': str(col.type),
                        'primary_key': col.primary_key,
                        'foreign_key': next(iter(col.foreign_keys)).target_fullname if col.foreign_keys else None,
                        'nullable': col.nullable
                    }
                    for col in table.columns
                ]
            }
        
        with open(filepath, 'w') as f:
            json.dump(schema_def, f, indent=2) 
    
    def truncate_table(self, table_name: str) -> dict:
        """Truncate a table in the database"""
        try:
            with self.engine.begin() as conn:
                if table_name in self.tables:
                    conn.execute(self.tables[table_name].delete())
                    return {
                        "success": True,
                        "message": f"Table {table_name} truncated successfully"
                    }
                return {
                    "success": False,
                    "error": f"Table {table_name} does not exist"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def set_table_comment(self, table_name: str, comment: str) -> dict:
        """Set a comment on a table"""
        try:
            if table_name in self.tables:
                table = self.tables[table_name]
                table.comment = comment
                with self.engine.begin() as conn:
                    # MySQL specific comment syntax
                    conn.execute(text(
                        f"ALTER TABLE {table_name} COMMENT = '{comment}'"
                    ))
                return {
                    "success": True,
                    "message": f"Comment added to table {table_name}"
                }
            return {
                "success": False,
                "error": f"Table {table_name} does not exist"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def set_column_comment(self, table_name: str, column_name: str, comment: str) -> dict:
        """Set a comment on a column"""
        try:
            if table_name in self.tables:
                table = self.tables[table_name]
                if column_name in table.columns:
                    with self.engine.begin() as conn:
                        # Get column type and other properties
                        column = table.columns[column_name]
                        col_type = str(column.type)
                        nullable = "NULL" if column.nullable else "NOT NULL"
                        
                        # MySQL specific column comment syntax
                        conn.execute(text(
                            f"ALTER TABLE {table_name} MODIFY COLUMN {column_name} "
                            f"{col_type} {nullable} COMMENT '{comment}'"
                        ))
                    return {
                        "success": True,
                        "message": f"Comment added to column {column_name} in table {table_name}"
                    }
                return {
                    "success": False,
                    "error": f"Column {column_name} does not exist in table {table_name}"
                }
            return {
                "success": False,
                "error": f"Table {table_name} does not exist"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def rename_table(self, old_name: str, new_name: str) -> dict:
        """Rename a table in the database"""
        try:
            if old_name in self.tables:
                with self.engine.begin() as conn:
                    conn.execute(f"ALTER TABLE {old_name} RENAME TO {new_name}")
                    # Update internal references
                    self.tables[new_name] = self.tables.pop(old_name)
                    # Update relationships
                    for rel in self.relationships:
                        if rel['from'] == old_name:
                            rel['from'] = new_name
                        if rel['to'] == old_name:
                            rel['to'] = new_name
                    return {
                        "success": True,
                        "message": f"Table {old_name} renamed to {new_name}"
                    }
            return {
                "success": False,
                "error": f"Table {old_name} does not exist"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _check_graphviz(self):
        """Check if GraphViz is installed and accessible"""
        try:
            import graphviz
            # Try to create and render a simple test graph
            test_dot = graphviz.Digraph(comment='Test')
            test_dot.node('A', 'Test Node')
            test_path = "test_graphviz"
            test_dot.render(test_path, format='png', cleanup=True)
            # Clean up test file
            if os.path.exists(f"{test_path}.png"):
                os.remove(f"{test_path}.png")
            return True, "GraphViz is working correctly"
        except Exception as e:
            import sys
            import platform
            
            # Get system information
            sys_info = {
                "OS": platform.system(),
                "PATH": os.environ.get("PATH", ""),
                "Python": sys.version,
                "Error": str(e)
            }
            
            return False, f"""GraphViz check failed:
            Operating System: {sys_info['OS']}
            Python Version: {sys_info['Python']}
            Error Message: {sys_info['Error']}
            PATH: {sys_info['PATH']}
            """

    def visualize_table(self, table_name: str, output_path: str = "table_viz"):
        """Generate visualization for a single table"""
        # Check GraphViz installation
        graphviz_ok, message = self._check_graphviz()
        if not graphviz_ok:
            return f"ERROR: GraphViz issue detected:\n{message}"
        
        try:
            import graphviz
            dot = graphviz.Digraph(comment=f'Table: {table_name}')
            dot.attr(rankdir='LR')
            
            # Create HTML-like label for table
            label = f'''<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
                <TR><TD PORT="header" BGCOLOR="#4CAF50"><B>{table_name}</B></TD></TR>'''
            
            # Add columns
            table = self.tables[table_name]
            for col in table['columns']:
                pk_marker = "🔑 " if col.get('primary_key') else ""
                fk_marker = "🔗 " if col.get('foreign_key', {}).get('is_fk') else ""
                label += f'<TR><TD PORT="{col["name"]}">{pk_marker}{fk_marker}{col["name"]}: {col["type"]}</TD></TR>'
            
            label += '</TABLE>>'
            dot.node(table_name, label=label, shape='none')
            
            # Save visualization
            os.makedirs(output_path, exist_ok=True)
            file_path = os.path.join(output_path, f"{table_name}")
            dot.render(file_path, format='png', cleanup=True)
            return f"{file_path}.png"
        except Exception as e:
            import traceback
            return f"""ERROR: Failed to generate visualization
            Error: {str(e)}
            Traceback: {traceback.format_exc()}""" 
    
    def add_column(self, table_name: str, column_info: Dict) -> dict:
        """Add a column to an existing table"""
        try:
            if table_name not in self.tables:
                return {
                    "success": False,
                    "error": f"Table {table_name} does not exist"
                }

            # Get SQL type
            sql_type = self._get_sql_type(column_info['type'])
            
            # Create new column
            new_column = Column(
                column_info['name'],
                sql_type,
                primary_key=column_info.get('primary_key', False),
                nullable=column_info.get('nullable', True)
            )

            # Add column to database
            with self.engine.begin() as conn:
                # Create the column
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_info['name']} {column_info['type']}"))
                
                # Add constraints if any
                if not column_info.get('nullable', True):
                    conn.execute(text(f"ALTER TABLE {table_name} MODIFY {column_info['name']} {column_info['type']} NOT NULL"))
                
                if column_info.get('foreign_key', {}).get('is_fk'):
                    ref_table, ref_column = column_info['foreign_key']['references'].split('.')
                    conn.execute(text(
                        f"ALTER TABLE {table_name} ADD FOREIGN KEY ({column_info['name']}) "
                        f"REFERENCES {ref_table}({ref_column})"
                    ))

            # Update internal schema representation
            if isinstance(self.tables[table_name], Table):
                # For SQLAlchemy Table objects
                self.tables[table_name].append_column(new_column)
            else:
                # For dictionary representation
                self.tables[table_name]['columns'].append({
                    'name': column_info['name'],
                    'type': str(sql_type),
                    'nullable': column_info.get('nullable', True),
                    'primary_key': column_info.get('primary_key', False),
                    'foreign_key': column_info.get('foreign_key', {'is_fk': False})
                })

            return {
                "success": True,
                "message": f"Column {column_info['name']} added to table {table_name}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def drop_column(self, table_name: str, column_name: str) -> dict:
        """Drop a column from a table"""
        try:
            if table_name not in self.tables:
                return {
                    "success": False,
                    "error": f"Table {table_name} does not exist"
                }

            table = self.tables[table_name]
            if column_name not in table.columns:
                return {
                    "success": False,
                    "error": f"Column {column_name} does not exist in table {table_name}"
                }

            with self.engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table_name} DROP COLUMN {column_name}"))

            # Update internal schema
            table.columns.remove(table.columns[column_name])
            
            return {
                "success": True,
                "message": f"Column {column_name} dropped from table {table_name}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def modify_column(self, table_name: str, column_info: Dict) -> dict:
        """Modify a column in a table"""
        try:
            if table_name not in self.tables:
                return {
                    "success": False,
                    "error": f"Table {table_name} does not exist"
                }

            table = self.tables[table_name]
            if column_info['name'] not in table.columns:
                return {
                    "success": False,
                    "error": f"Column {column_info['name']} does not exist in table {table_name}"
                }

            with self.engine.begin() as conn:
                # Modify column type and constraints
                modify_sql = f"ALTER TABLE {table_name} MODIFY {column_info['name']} {column_info['type']}"
                if not column_info.get('nullable', True):
                    modify_sql += " NOT NULL"
                conn.execute(text(modify_sql))

                # Handle foreign key changes if needed
                if column_info.get('foreign_key', {}).get('is_fk'):
                    ref_table, ref_column = column_info['foreign_key']['references'].split('.')
                    conn.execute(text(
                        f"ALTER TABLE {table_name} ADD FOREIGN KEY ({column_info['name']}) "
                        f"REFERENCES {ref_table}({ref_column})"
                    ))

            # Update internal schema
            column_type = self._get_sql_type(column_info['type'])
            new_column = Column(
                column_info['name'],
                column_type,
                primary_key=column_info.get('primary_key', False),
                nullable=column_info.get('nullable', True)
            )
            table.columns[column_info['name']] = new_column

            return {
                "success": True,
                "message": f"Column {column_info['name']} modified in table {table_name}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            } 