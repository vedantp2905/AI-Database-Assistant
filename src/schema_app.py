import os
from dotenv import load_dotenv
from schema_manager import SchemaManager
from schema_designer import SchemaDesigner
from schema_assistant import SchemaAssistant
import requests
from sqlalchemy import text
import pandas as pd
import time
import tempfile
import sys
import streamlit as st
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
        
        .welcome-container {
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            text-align: center;
        }
        
        .schema-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin-top: 2rem;
        }
        
        .schema-card {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 1.5rem 1.5rem 0.5rem 1.5rem;
            text-align: center;
            transition: transform 0.2s, box-shadow 0.2s;
            margin-bottom: 0.5rem;
        }
        
        .schema-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        
        .schema-card h3 {
            margin: 0 0 1rem 0;
            color: #1a1a1a;
        }
        
        [data-testid="stButton"] button {
            background-color: #4CAF50 !important;
            color: white !important;
            border: none !important;
            padding: 0.5rem 1rem !important;
            border-radius: 4px !important;
            width: calc(100% - 3rem);
            margin: 0 1.5rem;
        }
        
        [data-testid="stButton"] button:hover {
            background-color: #45a049 !important;
        }
        
        .create-new-section {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 1.5rem;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
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
        
        .split-view {
            display: flex;
            gap: 2rem;
        }
        
        .split-view-left {
            flex: 1;
            min-width: 0;
            padding-right: 1rem;
            border-right: 1px solid #e0e0e0;
        }
        
        .split-view-right {
            flex: 1;
            min-width: 0;
            padding-left: 1rem;
        }
        
        .schema-viewer {
            position: sticky;
            top: 3rem;
            max-height: calc(100vh - 6rem);
            overflow-y: auto;
        }
        
        /* New styles for builder page */
        .builder-header {
            background: linear-gradient(90deg, #1a1a1a 0%, #2d2d2d 100%);
            color: white;
            padding: 2rem;
            border-radius: 8px;
            margin-bottom: 2rem;
            text-align: center;
        }
        
        .danger-button button {
            background-color: #dc3545 !important;
            color: white !important;
            border: none !important;
            padding: 0.5rem 1rem !important;
            border-radius: 4px !important;
            width: 100% !important;
            margin: 0 !important;
        }
        
        .danger-button button:hover {
            background-color: #c82333 !important;
            color: white !important;
        }
        
        .danger-button button:active, 
        .danger-button button:focus {
            background-color: #bd2130 !important;
            color: white !important;
        }
        
        .assistant-input {
            background: #f8f9fa;
            padding: 2rem;
            border-radius: 8px;
            margin-bottom: 2rem;
        }
        
        .schema-history {
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            border: 1px solid #e9ecef;
            margin-top: 2rem;
        }
        
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin: 2rem 0;
        }
        
        .feature-card {
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            border: 1px solid #e9ecef;
            text-align: center;
        }
        
        .feature-card i {
            font-size: 2rem;
            margin-bottom: 1rem;
            color: #4CAF50;
        }
        
        /* Override Streamlit's default button styling with !important */
        div[data-testid="stHorizontalBlock"] div.danger-button button,
        div[data-testid="stHorizontalBlock"] div.danger-button button[kind="secondary"],
        div.danger-button button[kind="secondary"],
        .danger-button button {
            background-color: #dc3545 !important;
            color: white !important;
            border: none !important;
            padding: 0.5rem 1rem !important;
            border-radius: 4px !important;
            width: 100% !important;
            margin: 0 !important;
        }
        
        /* Override hover state */
        div[data-testid="stHorizontalBlock"] div.danger-button button:hover,
        div[data-testid="stHorizontalBlock"] div.danger-button button[kind="secondary"]:hover,
        div.danger-button button[kind="secondary"]:hover,
        .danger-button button:hover {
            background-color: #c82333 !important;
            color: white !important;
            border-color: #bd2130 !important;
        }
        
        /* Override active/focus state */
        div[data-testid="stHorizontalBlock"] div.danger-button button:active,
        div[data-testid="stHorizontalBlock"] div.danger-button button:focus,
        div.danger-button button[kind="secondary"]:active,
        div.danger-button button[kind="secondary"]:focus,
        .danger-button button:active,
        .danger-button button:focus {
            background-color: #bd2130 !important;
            color: white !important;
            border-color: #b21f2d !important;
        }
        
        /* Query interface link styling */
        .query-link {
            display: inline-block;
            padding: 1rem 2rem;
            background-color: #4CAF50;
            color: white !important;
            text-decoration: none;
            border-radius: 4px;
            margin: 1rem 0;
            text-align: center;
            font-weight: bold;
            transition: background-color 0.2s;
        }
        
        .query-link:hover {
            background-color: #45a049;
            text-decoration: none;
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
            
            # Initialize SchemaManager with skip_embeddings=True for schema creation
            st.session_state.schema_manager = SchemaManager(
                db_url=db_connection_url,
                schema_name=schema_name,
                skip_embeddings=True
            )
            
            # Use the engine_url from SchemaManager for consistency
            st.session_state.designer = SchemaDesigner(
                db_url=st.session_state.schema_manager.engine_url
            )
            
            # Initialize SchemaAssistant with schema name
            st.session_state.assistant = SchemaAssistant(
                db_url=st.session_state.schema_manager.engine_url,
                schema_name=schema_name
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
        
        # Use system temp directory instead of local folder
        temp_dir = tempfile.gettempdir()
        output_file = os.path.join(temp_dir, f"{st.session_state.schema_name}_erd")
        
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
            splines="polyline",  # Changed from ortho to polyline for better label handling
            nodesep="1.0",    # Increased node separation
            ranksep="1.5",    # Increased rank separation
            concentrate="false" # Disabled edge concentration for clearer labels
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

        # Add relationships with improved styling and xlabel
        for table, column, ref_table, ref_column in relationships:
            dot.edge(
                f"{table}:{column}:e",
                f"{ref_table}:{ref_column}:w",
                arrowhead="crow",
                arrowtail="none",
                color="#2196F3",
                penwidth="1.5",
                xlabel=f"{column} → {ref_column}"  # Changed from label to xlabel
            )

        # Render with higher DPI and better quality settings
        dot.render(output_file, cleanup=True, format="png")
        cursor.close()
        conn.close()
        return f"{output_file}.png", None
            
    except Exception as e:
        return None, f"Failed to generate ERD: {str(e)}"

def display_schema_viewer():
    """Display schema structure and ERD"""
    # ERD Section first
    st.subheader("Entity Relationship Diagram")
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
    
    st.divider()
    
    # Table details
    schema_info = st.session_state.schema_manager.get_schema_info()
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

def display_schema_history():
    """Display schema modification history"""
    try:
        history = st.session_state.assistant.get_history()
        
        for entry in history:
            with st.chat_message(entry["role"]):
                if entry["role"] == "assistant" and "sql" in entry:
                    st.write("Successfully executed SQL:")
                    st.code(entry["sql"], language="sql")
                else:
                    st.write(entry["content"])
                
                st.caption(f"Time: {entry['timestamp']}")
    except Exception as e:
        st.error(f"Error displaying history: {str(e)}")

def schema_assistant_tab():
    # Welcome header
    st.markdown("""
        <div class="builder-header">
            <h1>🏗️ Database Builder</h1>
            <p>Design and modify your database schema using natural language</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Feature cards
    st.markdown("""
        <div class="feature-grid">
            <div class="feature-card">
                <div>🏗️ Create Your Database</div>
                <p>Design new tables with custom columns and relationships</p>
            </div>
            <div class="feature-card">
                <div>🔄 Modify Your Database</div>
                <p>Add, modify, or remove columns and tables</p>
            </div>
            <div class="feature-card">
                <div>🔗 No knowledge of SQL</div>
                <p>No need to know SQL, just use natural language</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Create two columns for the main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Input area - removed the assistant-input div wrapper
        if "schema_input" not in st.session_state:
            st.session_state.schema_input = ""
        
        user_input = st.text_area(
            "What would you like to do with the schema?", 
            value=st.session_state.schema_input,
            placeholder="e.g., Create a new users table with email and password columns",
            height=100,
            key="schema_input"
        )
        
        if st.button("🚀 Execute Changes", type="primary", use_container_width=True):
            with st.spinner("Processing..."):
                result = st.session_state.assistant.process_command(user_input)
                if result['success']:
                    st.success("Successfully executed SQL")
                    st.code(result['sql'], language='sql')
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(result['error'])
        
        # History section
        st.markdown('<div class="schema-history">', unsafe_allow_html=True)
        st.markdown("### 📝 Schema Modification History")
        display_schema_history()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        # Current schema viewer
        display_current_schema()

def display_current_schema():
    """Helper function to display current schema state"""
    if 'schema_manager' not in st.session_state:
        return
    
    # ERD Section - Moved to top and expanded by default
    with st.expander("Entity Relationship Diagram", expanded=True):
        with st.spinner("Generating ERD..."):
            erd_path, error = get_schema_erd()
            if erd_path:
                st.image(erd_path, use_container_width=True)
            else:
                st.error(f"Failed to generate ERD: {error}")
    
    # Table details - Now below ERD and collapsed by default
    schema_info = st.session_state.schema_manager.get_schema_info()
    for table in schema_info:
        with st.expander(f"📋 {table['table_name']}", expanded=False):  # Changed expanded to False
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

def delete_current_schema():
    """Delete current schema and clean up resources"""
    try:
        schema_name = st.session_state.schema_name
        
        # Delete vector store first
        if 'schema_manager' in st.session_state:
            print(f"[DEBUG] Deleting vector store for schema: {schema_name}")
            st.session_state.schema_manager.delete_vector_store()
        
        # Delete history file
        if 'assistant' in st.session_state:
            print(f"[DEBUG] Cleaning up assistant resources")
            st.session_state.assistant.cleanup()
        
        # Delete the schema from database
        print(f"[DEBUG] Dropping schema from database")
        with st.session_state.base_schema_manager.engine.connect() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name}"))
            conn.commit()
        
        # Clear session state
        print(f"[DEBUG] Clearing session state")
        for key in ['schema_name', 'schema_manager', 'designer', 'assistant']:
            if key in st.session_state:
                del st.session_state[key]
        
        st.rerun()
        
    except Exception as e:
        print(f"[DEBUG] Error in delete_current_schema: {str(e)}")
        st.error(f"Failed to delete database: {str(e)}")

def query_database_tab():
    # Welcome header
    st.markdown("""
        <div class="builder-header">
            <h1>🔍 Query Database</h1>
            <p>Explore and analyze your data using natural language</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Feature cards
    st.markdown("""
        <div class="feature-grid">
            <div class="feature-card">
                <div>💬 Natural Language</div>
                <p>Ask questions in plain English - no SQL needed</p>
            </div>
            <div class="feature-card">
                <div>📊 Data Visualization</div>
                <p>Automatic charts and graphs for your data</p>
            </div>
            <div class="feature-card">
                <div>🔍 Smart Search</div>
                <p>Context-aware queries across your schema</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Main content
    st.markdown("""
        <div class="assistant-input">
            <h3>🚀 Launch Query Interface</h3>
            <p>Start exploring your data with our interactive query interface:</p>
            <ul>
                <li>Ask questions in natural language</li>
                <li>Get instant SQL translations</li>
                <li>View data visualizations</li>
                <li>Explore your database schema</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚀 Launch Query Interface", type="primary", use_container_width=True):
        try:
            st.success("Query interface launched!")
            st.markdown("""
                <div class="schema-history">
                    <h3>🔗 Access Your Query Interface</h3>
                    <p>Your query interface is ready! Click the button below to start exploring:</p>
                    <a href="http://localhost:8502" target="_blank" class="query-link">
                        🚀 Open Query Interface
                    </a>
                </div>
            """, unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Failed to launch query interface: {str(e)}")

def delete_database():
    try:
        schema_name = st.session_state.schema_name
        print(f"[DEBUG] Deleting database: {schema_name}")
        
        # Create a new SchemaManager instance specifically for deletion
        deletion_manager = SchemaManager(
            db_url=os.getenv("DATABASE_CONNECTION_URL"),
            schema_name=schema_name,
            skip_embeddings=True  # Skip embeddings since we're deleting
        )
        
        # Delete schema history
        if 'assistant' in st.session_state:
            print("[DEBUG] Deleting schema history")
            st.session_state.assistant.history_manager.clear_history()
        
        # Delete vector store
        print("[DEBUG] Attempting to delete vector store")
        deletion_manager.delete_vector_store()
        
        # Delete the database
        print("[DEBUG] Dropping database")
        with st.session_state.base_schema_manager.engine.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS {schema_name}"))
        print("[DEBUG] Database dropped successfully")
        
        # Clear session state
        print("[DEBUG] Clearing session state")
        for key in ['schema_name', 'schema_manager', 'designer', 'assistant']:
            if key in st.session_state:
                del st.session_state[key]
        
        st.success("Database deleted successfully!")
        st.rerun()
        
    except Exception as e:
        print(f"[DEBUG] Error in delete_database: {str(e)}")
        st.error(f"Failed to delete database: {str(e)}")

def main():
    # Add port configuration
    if '--server.port' not in sys.argv:
        sys.argv.extend(['--server.port', '8501'])
    
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
        st.markdown("""
            <div class="welcome-container">
                <h1>🏗️ Welcome to Schema Builder</h1>
                <p>Connect to an existing database or create a new one to get started.</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Get available schemas
        available_schemas = st.session_state.base_schema_manager.get_available_schemas()
        
        if available_schemas:
            # Create a 3-column layout with 2:2:1 ratio
            col1, col2, col3 = st.columns([2, 2, 1.5])
            
            # Split schemas into two groups for the first two columns
            mid_point = (len(available_schemas) + 1) // 2
            first_half = available_schemas[:mid_point]
            second_half = available_schemas[mid_point:]
            
            # First column of schemas
            with col1:
                for schema in first_half:
                    st.markdown(f"""
                        <div class="schema-card">
                            <h3>📁 {schema}</h3>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button("Connect", key=f"connect_{schema}", type="primary"):
                        st.session_state.schema_name = schema
                        if initialize_session_state():
                            st.rerun()
            
            # Second column of schemas
            with col2:
                for schema in second_half:
                    st.markdown(f"""
                        <div class="schema-card">
                            <h3>📁 {schema}</h3>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button("Connect", key=f"connect_{schema}_2", type="primary"):
                        st.session_state.schema_name = schema
                        if initialize_session_state():
                            st.rerun()
            
            # Create new database section in third column
            with col3:
                st.markdown("""
                    <div class="create-new-section">
                        <h2>Create New Database</h2>
                        <p>Create a new database below</p>
                    </div>
                """, unsafe_allow_html=True)
                
                new_schema_name = st.text_input(
                    "Database name:",
                    placeholder="e.g., my_new_database"
                )
                
                if new_schema_name:
                    if new_schema_name in available_schemas:
                        st.error(f"Database '{new_schema_name}' already exists.")
                    elif st.button("Create Database", type="primary"):
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
        
        # Add tabs for different functionalities
        tab1, tab2 = st.tabs(["🛠️ Database Builder", "🔍 Query Database"])
        
        with tab1:
            # Add delete and clear buttons only in builder tab
            col1, col2, col3 = st.columns([8, 2, 2])
            with col2:
                st.markdown('<div class="danger-button">', unsafe_allow_html=True)
                if st.button("🗑️ Clear History", type="secondary", use_container_width=True):
                    if 'assistant' in st.session_state:
                        st.session_state.assistant.history_manager.clear_history()
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col3:
                st.markdown('<div class="danger-button">', unsafe_allow_html=True)
                if st.button("🗑️ Delete Database", type="secondary", use_container_width=True):
                    delete_current_schema()
                st.markdown('</div>', unsafe_allow_html=True)
            
            schema_assistant_tab()
        
        with tab2:
            # Only show delete database button in query tab
            col1, col2 = st.columns([10, 2])
            with col2:
                st.markdown('<div class="danger-button">', unsafe_allow_html=True)
                if st.button("🗑️ Delete Database", key="delete_db_query", type="secondary", use_container_width=True):
                    delete_current_schema()
                st.markdown('</div>', unsafe_allow_html=True)
            
            query_database_tab()

if __name__ == "__main__":
    main() 

