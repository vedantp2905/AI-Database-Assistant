import streamlit as st
import os
from dotenv import load_dotenv
from schema_manager import SchemaManager
from schema_designer import SchemaDesigner
from schema_assistant import SchemaAssistant
import plotly.express as px
from streamlit_lottie import st_lottie
import requests
from sqlalchemy import text
import pandas as pd
import re
import subprocess
from pathlib import Path
import graphviz

def load_lottie_url(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

def load_css():
    st.markdown("""
        <style>
        .stApp {
            background: #ffffff;
            color: #333333;
        }
        
        [data-testid="stSidebar"] {
            background-color: #1a1a1a;
            padding: 1rem;
            color: #ffffff;
        }
        
        .schema-card {
            background-color: #ffffff;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        }
        
        .table-header {
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .column-list {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .column-item {
            display: flex;
            justify-content: space-between;
            padding: 0.5rem;
            background-color: #f8f8f8;
            border-radius: 4px;
        }
        
        .success-message {
            padding: 1rem;
            background-color: #d4edda;
            color: #155724;
            border-radius: 4px;
            margin: 1rem 0;
        }
        
        .error-message {
            padding: 1rem;
            background-color: #f8d7da;
            color: #721c24;
            border-radius: 4px;
            margin: 1rem 0;
        }
        </style>
    """, unsafe_allow_html=True)

def initialize_session_state():
    if 'schema_manager' not in st.session_state:
        try:
            load_dotenv()
            db_connection_url = os.getenv("DATABASE_CONNECTION_URL").rstrip('/')
            schema_name = st.session_state.get('schema_name')
            
            if not schema_name:
                st.error("Schema name not set")
                return False
            
            # Initialize SchemaManager with base URL and schema name
            st.session_state.schema_manager = SchemaManager(
                db_url=db_connection_url,
                schema_name=schema_name
            )
            
            # Use the engine_url from SchemaManager for consistency
            st.session_state.designer = SchemaDesigner(
                db_url=st.session_state.schema_manager.engine_url
            )
            st.session_state.assistant = SchemaAssistant(
                db_url=st.session_state.schema_manager.engine_url
            )
            return True
            
        except Exception as e:
            st.error(f"Failed to initialize database: {str(e)}")
            if 'schema_name' in st.session_state:
                del st.session_state.schema_name
            return False
    
    if 'current_table' not in st.session_state:
        st.session_state.current_table = None
    
    if 'show_success' not in st.session_state:
        st.session_state.show_success = False
    
    if 'success_message' not in st.session_state:
        st.session_state.success_message = ""
    
    return True

def get_schema_erd():
    """Generate high-quality ERD using MySQL INFORMATION_SCHEMA"""
    try:
        import mysql.connector
        from graphviz import Digraph
        from urllib.parse import urlparse
        
        # Parse database URL for connection
        db_url = os.getenv("DATABASE_CONNECTION_URL")
        parsed = urlparse(db_url)
        
        # Connect to MySQL database
        conn = mysql.connector.connect(
            host=parsed.hostname,
            user=parsed.username,
            password=parsed.password,
            database=st.session_state.schema_name,
            port=parsed.port or 3306
        )
        cursor = conn.cursor()

        # Get table columns and relationships
        cursor.execute("""
            SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s;
        """, (st.session_state.schema_name,))
        columns = cursor.fetchall()

        cursor.execute("""
            SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s AND REFERENCED_TABLE_NAME IS NOT NULL;
        """, (st.session_state.schema_name,))
        relationships = cursor.fetchall()

        # Generate ERD with enhanced settings
        dot = Digraph("ERD", format="png")
        dot.attr(
            rankdir="LR",
            splines="ortho",  # Orthogonal lines for cleaner look
            nodesep="0.8",    # Increased space between nodes
            ranksep="1.0",    # Increased rank separation
            concentrate="true" # Merge edges for cleaner diagram
        )
        
        # Set global graph attributes for better quality
        dot.attr('graph',
            fontname="Arial",
            fontsize="16",
            pad="0.5",
            dpi="300"  # Higher DPI for better quality
        )
        
        # Set node attributes
        dot.attr('node',
            fontname="Arial",
            fontsize="12",
            shape="none",
            margin="0",
            style="rounded"
        )
        
        # Set edge attributes
        dot.attr('edge',
            fontname="Arial",
            fontsize="10",
            len="1.5"
        )

        # Add tables and relationships
        tables = {}
        for table, column, column_type in columns:
            if table not in tables:
                tables[table] = []
            tables[table].append(f"{column} ({column_type})")
        
        for table, cols in tables.items():
            # Enhanced HTML-like label with better styling
            label = f'''<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="8">
                <TR><TD PORT="header" BGCOLOR="#4CAF50" COLOR="white"><B>{table}</B></TD></TR>'''
            
            # Add columns with alternating background colors for better readability
            for i, col in enumerate(cols):
                bg_color = '#f8f8f8' if i % 2 == 0 else 'white'
                label += f'<TR><TD PORT="{col.split()[0]}" BGCOLOR="{bg_color}" ALIGN="LEFT">{col}</TD></TR>'
            label += '</TABLE>>'
            
            dot.node(table, label=label)

        # Add relationships with improved styling
        for table, column, ref_table, ref_column in relationships:
            dot.edge(
                f"{table}:{column}:e",
                f"{ref_table}:{ref_column}:w",
                arrowhead="crow",
                arrowtail="none",
                color="#2196F3",
                penwidth="1.5",
                label=f" {column} → {ref_column} "
            )

        # Create temporary directory and render with high quality settings
        temp_dir = "temp_erd"
        os.makedirs(temp_dir, exist_ok=True)
        output_file = os.path.join(temp_dir, f"{st.session_state.schema_name}_erd")
        
        # Render with higher DPI and better quality settings
        dot.render(output_file, cleanup=True, format="png")
        cursor.close()
        conn.close()
        return f"{output_file}.png", None
            
    except Exception as e:
        return None, f"Failed to generate ERD: {str(e)}"

def display_schema_viewer():
    st.header("Schema Viewer")
    
    # Add tabs for different views
    tab1, tab2 = st.tabs(["Table Details", "Entity Relationship Diagram"])
    
    with tab1:
        schema_info = st.session_state.schema_manager.get_schema_info()
        # Table details code remains the same
        for table in schema_info:
            with st.expander(f"📋 {table['table_name']}", expanded=False):
                columns = []
                for col in table['columns']:
                    col_type = col['type']
                    attributes = []
                    if col.get('primary_key'):
                        attributes.append('🔑 PK')
                    if col.get('foreign_key', {}).get('is_fk'):
                        attributes.append('🔗 FK')
                    if not col.get('nullable', True):
                        attributes.append('Required')
                    
                    columns.append({
                        'Column': col['name'],
                        'Type': col_type,
                        'Attributes': ' | '.join(attributes) if attributes else ''
                    })
                
                df = pd.DataFrame(columns)
                st.dataframe(
                    df,
                    hide_index=True,
                    use_container_width=True
                )
    
    with tab2:
        with st.spinner("Generating Entity Relationship Diagram..."):
            erd_path, error = get_schema_erd()
            if erd_path:
                # Create three columns to center the image
                left_col, center_col, right_col = st.columns([1, 2, 1])
                
                with center_col:
                    st.image(erd_path, width=800)
                    st.download_button(
                        label="Download ERD",
                        data=open(erd_path, "rb").read(),
                        file_name=f"{st.session_state.schema_name}_erd.png",
                        mime="image/png",
                        use_container_width=True
                    )
            else:
                st.error(f"Failed to generate ERD: {error}")

def schema_assistant_tab():
    st.header("Schema Assistant")
    
    user_input = st.text_area(
        "What would you like to do with the schema?", 
        placeholder="e.g., Create a new users table with email and password columns"
    )
    
    if st.button("Execute"):
        with st.spinner("Processing..."):
            result = st.session_state.assistant.process_command(user_input)
            if result['success']:
                st.success(result['message'])
                st.code(result['sql'], language='sql')
            else:
                st.error(result['error'])

def main():
    st.set_page_config(
        page_title="Database Schema Manager",
        page_icon="🗃️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    load_css()
    
    # Initialize basic SchemaManager for getting schemas
    if 'base_schema_manager' not in st.session_state:
        load_dotenv()
        db_connection_url = os.getenv("DATABASE_CONNECTION_URL")
        st.session_state.base_schema_manager = SchemaManager(db_url=db_connection_url)
    
    # Add schema selection if not already set
    if 'schema_name' not in st.session_state:
        st.title("Welcome to Schema Manager")
        
        # Get available schemas
        available_schemas = st.session_state.base_schema_manager.get_available_schemas()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Select Existing Database")
            if available_schemas:
                selected_schema = st.selectbox(
                    "Choose an existing database:",
                    available_schemas,
                    index=None,
                    placeholder="Select a database..."
                )
                if selected_schema and st.button("Connect to Database"):
                    st.session_state.schema_name = selected_schema
                    if initialize_session_state():
                        st.rerun()
        
        with col2:
            st.subheader("Create New Database")
            new_schema_name = st.text_input(
                "Enter a name for your new Database:",
                placeholder="e.g., my_new_database"
            )
            if new_schema_name:
                # Check if schema already exists
                if new_schema_name in available_schemas:
                    st.error(f"Database '{new_schema_name}' already exists. Please choose a different name.")
                elif st.button("Create Database"):
                    try:
                        with st.session_state.base_schema_manager.engine.connect() as conn:
                            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {new_schema_name}"))
                        st.session_state.schema_name = new_schema_name
                        if initialize_session_state():
                            st.success(f"Database '{new_schema_name}' created successfully!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Failed to create database: {str(e)}")
    else:
        # Main application UI after schema is selected
        st.title(f"Schema Manager - {st.session_state.schema_name}")
        
        # Create tabs for different functionalities
        tab1, tab2 = st.tabs(["Database Builder", "Database Viewer"])
        
        with tab1:
            st.markdown("""
            ### 🛠️ Database Builder
            
            Use natural language to modify your database structure. You can:
            - Create new tables with columns
            - Add or modify columns in existing tables
            - Set up relationships between tables
            - Add comments to tables and columns
            - Rename or drop tables
            
            Just describe what you want to do in plain English, and I'll help you build it!
            
            Example commands:
            - Creating a database:  To track zoos, animals, staff. staff work at zoos and are assigned to animals. animals can be transferred so need to track which zoo they are at 
            - Altering a database: Staff will need salary and hours worked
            - Altering a database: Zoos will need to track the number of animals they have
            - Truncating a table: Delete all data from the zoos table
            - Renaming a table: rename the zoos table to zoo_info
            
            Limitations:
            - Cant edit data types as of now
            """)
            schema_assistant_tab()
        
        with tab2:
            st.markdown("""
            ### 📊 Database Viewer
            
            Explore your database structure through different views:
            
            **Table Details:**
            - View all tables and their columns
            - See data types and constraints
            - Identify primary keys (🔑) and foreign keys (🔗)
            - Check column requirements
            
            **Entity Relationship Diagram (ERD):**
            - Visual representation of your database
            - See relationships between tables
            - Download the ERD for documentation
            - Interactive diagram with table details
            """)
            display_schema_viewer()

if __name__ == "__main__":
    main() 