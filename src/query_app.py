import warnings
import os
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', module='torch.classes')
import streamlit as st
from dotenv import load_dotenv
from schema_manager import SchemaManager
from chatbot import DBChatbot
import pandas as pd
import plotly.express as px
from streamlit_lottie import st_lottie
import requests
import tempfile

# Custom CSS for better styling
def load_css():
    st.markdown("""
        <style>
        /* Main app styling */
        .stApp {
            background: #ffffff;
            color: #333333;
        }
        
        /* Sidebar styling - keep dark */
        [data-testid="stSidebar"] {
            background-color: #1a1a1a;
            padding: 1rem;
            border-right: 1px solid #333;
            color: #ffffff;
        }
        [data-testid="stSidebarNav"] {
            background-color: #1a1a1a;
            color: #ffffff;
        }
        
        /* Keep sidebar text white */
        [data-testid="stSidebar"] .stMarkdown {
            color: #ffffff !important;
        }
        
        /* Make selectbox text white */
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {
            color: #ffffff !important;
        }
        
        /* Main content text color */
        .stMarkdown,
        .stDataFrame,
        [data-testid="stChatMessage"],
        .streamlit-expanderHeader,
        .streamlit-expanderContent {
            color: #333333 !important;
        }
        
        /* Chat container styling */
        .chat-history-container {
            flex-grow: 1;
            overflow-y: auto;
            margin-bottom: 100px;
        }
        
        /* Fixed chat input at bottom */
        .chat-input-container {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background-color: #ffffff;
            padding: 1rem 2rem;
            border-top: 1px solid #e0e0e0;
            z-index: 100;
        }
        
        /* Expander styling */
        .streamlit-expanderHeader {
            background-color: #f5f5f5;
            border-radius: 4px;
        }
        
        /* Legend styling - single line */
        .schema-legend {
            display: flex;
            gap: 20px;  /* Space between legend items */
            align-items: center;
            padding: 10px 0;
            margin-bottom: 15px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .legend-item {
            display: inline-flex;
            align-items: center;
            white-space: nowrap;
            margin-right: 20px;
        }
        
        /* Table styling */
        .table-card-compact {
            margin-bottom: 20px;
            padding: 15px 20px;  /* Reduced vertical padding */
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            background-color: #ffffff;
        }
        
        .table-header {
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 8px;  /* Reduced space below table name */
            padding-bottom: 8px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        /* Column layout */
        .column-list-compact {
            display: flex;
            flex-direction: column;  /* Stack columns vertically */
            gap: 8px;  /* Space between rows */
            padding: 10px;
        }
        
        /* Column item styling */
        .column-item {
            padding: 8px 16px;
            border-radius: 4px;
            background-color: #f8f8f8;
            margin: 4px 0;
            display: flex;
            gap: 30px;  /* Increased horizontal space between column elements */
        }
        
        .column-name {
            min-width: 150px;  /* Fixed width for column names */
        }
        
        .column-type {
            min-width: 120px;  /* Fixed width for types */
        }
        
        /* Clear History button styling */
        [data-testid="stSidebar"] button {
            color: #000000 !important;  /* Black text for Clear History */
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
        }
        
        [data-testid="stSidebar"] button:hover {
            background-color: #f0f0f0;
        }
        
        .schema-card {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 1.5rem 1.5rem 0.5rem 1.5rem;  /* Reduced bottom padding */
            text-align: center;
            transition: transform 0.2s, box-shadow 0.2s;
            margin-bottom: 0.5rem;  /* Add space for button */
        }
        
        .schema-card h3 {
            margin: 0 0 1rem 0;  /* Add bottom margin to schema name */
            color: #1a1a1a;
        }
        
        /* Style for the Connect button */
        [data-testid="stButton"] {
            margin-top: -0.5rem;  /* Pull button up closer to card */
        }
        
        [data-testid="stButton"] button {
            background-color: #4CAF50 !important;
            color: white !important;
            border: none !important;
            padding: 0.5rem 1rem !important;
            border-radius: 4px !important;
            width: calc(100% - 3rem);  /* Match card width */
            margin: 0 1.5rem;  /* Center button under card */
        }
        
        [data-testid="stButton"] button:hover {
            background-color: #45a049 !important;
        }
        </style>
    """, unsafe_allow_html=True)

def load_lottie_url(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

def initialize_session_state():
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'base_schema_manager' not in st.session_state:
        load_dotenv()
        db_url = os.getenv("DATABASE_CONNECTION_URL")
        st.session_state.base_schema_manager = SchemaManager(db_url)
    
    # Add schema selection if not already set
    if 'schema_name' not in st.session_state:
        available_schemas = st.session_state.base_schema_manager.get_available_schemas()
        
        # Create a centered container with max-width
        st.markdown("""
            <style>
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
                padding: 1.5rem;
                text-align: center;
                transition: transform 0.2s, box-shadow 0.2s;
                cursor: pointer;
            }
            .schema-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
            .schema-card h3 {
                margin: 0;
                color: #1a1a1a;
            }
            /* Style for the Connect button */
            [data-testid="stButton"] button {
                background-color: #4CAF50 !important;
                color: white !important;
                border: none !important;
                padding: 0.5rem 1rem !important;
                border-radius: 4px !important;
            }
            [data-testid="stButton"] button:hover {
                background-color: #45a049 !important;
            }
            .create-new-link {
                display: inline-block;
                margin-top: 2rem;
                padding: 1rem 2rem;
                background-color: #007bff;
                color: white !important;
                text-decoration: none;
                border-radius: 8px;
                transition: background-color 0.2s;
            }
            .create-new-link:hover {
                background-color: #0056b3;
                text-decoration: none;
                color: white !important;
            }
            /* Make all text in create-new-link white */
            .create-new-link * {
                color: white !important;
            }
            </style>
            <div class="welcome-container">
                <h1>🗄️ Database Chat Assistant</h1>
                <p>Connect to an existing database or create a new one to get started.</p>
            </div>
        """, unsafe_allow_html=True)
        
        if available_schemas:
            st.markdown('<div class="schema-grid">', unsafe_allow_html=True)
            
            # Create a column for each schema
            cols = st.columns(min(3, len(available_schemas)))
            for idx, schema in enumerate(available_schemas):
                col = cols[idx % 3]
                with col:
                    st.markdown(f"""
                        <div class="schema-card">
                            <h3>📁 {schema}</h3>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"Connect", key=f"connect_{schema}", type="primary"):
                        st.session_state.schema_name = schema
                        with st.spinner('Initializing chatbot...'):
                            schema_manager = SchemaManager(
                                db_url=os.getenv("DATABASE_CONNECTION_URL"),
                                schema_name=schema
                            )
                            
                            if not schema_manager.embeddings_exist():
                                with st.spinner('Generating schema embeddings...'):
                                    schema_manager.update_vector_store()
                            
                            llm_provider = st.sidebar.selectbox(
                                "Select LLM Provider",
                                ["gemini"],
                                help="Google's Gemini"
                            )
                            st.session_state.chatbot = DBChatbot(schema_manager, llm_provider)
                            st.session_state.schema_info = schema_manager.get_schema_info()
                            st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Remove the hidden selectbox and connect button
        
        # Update link color in the create new section
        st.markdown("""
            <div class="welcome-container">
                <p>Don't see your database?</p>
                <a href="http://localhost:8501" target="_blank" class="create-new-link" style="color: white !important;">
                    🏗️ Create New Database
                </a>
            </div>
        """, unsafe_allow_html=True)
        return
    
    # Initialize other session state variables if schema is selected
    if 'chatbot' not in st.session_state and 'schema_name' in st.session_state:
        with st.spinner('Initializing chatbot...'):
            schema_manager = SchemaManager(
                db_url=os.getenv("DATABASE_CONNECTION_URL"),
                schema_name=st.session_state.schema_name
            )
            
            # Always update embeddings with progress bar
            with st.spinner('Analyzing database schema...'):
                progress_bar = st.progress(0)
                schema_manager.update_vector_store(
                    progress_callback=lambda x: progress_bar.progress(x)
                )
                progress_bar.empty()
                st.success('Schema analysis complete!')
            
            llm_provider = st.sidebar.selectbox(
                "Select LLM Provider",
                ["sambanova", "gemini"],
                help="SambaNova (faster) or Google's Gemini"
            )
            st.session_state.chatbot = DBChatbot(schema_manager, llm_provider)
            st.session_state.schema_info = schema_manager.get_schema_info()

def display_chat_history():
    for i, message in enumerate(st.session_state.chat_history):
        with st.chat_message(message["role"]):
            st.write(message["content"])
            
            # For assistant messages, show SQL and results immediately after the response
            if message["role"] == "assistant" and "sql" in message:
                with st.expander("🔍 View SQL Query", expanded=False):
                    st.code(message["sql"], language="sql")
                
                if "data" in message and not message["data"].empty:
                    with st.expander("📊 View Data & Visualizations", expanded=False):
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.dataframe(
                                message["data"],
                                use_container_width=True,
                                hide_index=True
                            )
                        
                        with col2:
                            try:
                                numeric_cols = message["data"].select_dtypes(include=['float64', 'int64']).columns
                                if len(numeric_cols) >= 1:
                                    fig = px.bar(message["data"], 
                                               x=message["data"].columns[0], 
                                               y=numeric_cols[0],
                                               title="Data Visualization")
                                    fig.update_layout(
                                        plot_bgcolor='rgba(0,0,0,0)',
                                        paper_bgcolor='rgba(0,0,0,0)',
                                        font=dict(color='white')
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                            except Exception:
                                pass

def display_schema_viewer():
    with st.expander("📚 Database Schema Browser"):
        # Single line legend
        st.markdown("""
        <div class='schema-legend'>
            <span class='legend-item'>📋 Table</span>
            <span class='legend-item'>🔑 Primary Key</span>
            <span class='legend-item'>🔗 Foreign Key</span>
            <span class='legend-item'>📝 Column</span>
            <span class='legend-item'>🔢 Type</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Display tables
        for table in st.session_state.schema_info:
            st.markdown(f"""
            <div class='table-card-compact'>
                <div class='table-header'>📋 {table['table_name']}</div>
                <div class='column-list-compact'>
            """, unsafe_allow_html=True)
            
            for col in table['columns']:
                col_name = f"📝 {col['name']}"
                if col['primary_key']:
                    col_name += " 🔑"
                if col['foreign_key']['is_fk']:
                    col_name += " 🔗"
                    
                st.markdown(f"""
                    <div class='column-item'>
                        <span class='column-name'>{col_name}</span>
                        <span class='column-type'>🔢 {col['type']}</span>
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown("</div></div>", unsafe_allow_html=True)

def main():
    # Force set the port before any Streamlit commands
    import sys
    sys.argv = [arg for arg in sys.argv if '--server.port' not in arg]
    sys.argv.extend(['--server.port', '8502'])

    st.set_page_config(
        page_title="Chat with Your Database",
        page_icon="🗄️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    load_css()
    
    # Initialize session state first
    initialize_session_state()
    
    # Only show main interface if schema is selected
    if 'schema_name' not in st.session_state:
        return
        
    # Load and display animation
    lottie_url = "https://assets5.lottiefiles.com/packages/lf20_qp1q7mct.json"
    lottie_json = load_lottie_url(lottie_url)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🗄️ Chat with Your Database")
    with col2:
        if lottie_json:
            st_lottie(lottie_json, height=100, key="database_animation")
    
    warnings.filterwarnings('ignore', category=UserWarning, module='torch')
    
    # Sidebar with information and features
    with st.sidebar:
        st.header("🔍 Database Assistant")
        st.markdown("""
        Welcome to the intelligent database assistant! Ask questions in natural language 
        and get insights from your data.
        """)
        
        st.subheader("✨ Features")
        features = {
            "🤖 Natural Language": "Convert questions to SQL",
            "📊 Data Visualization": "Automatic charts and graphs",
            "🛡️ Security": "SQL injection prevention",
            "📝 Schema Aware": "Understands database structure"
        }
        for icon, feature in features.items():
            st.markdown(f"{icon} {feature}")
        
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()
    
    # Chat input at the top
    st.markdown('<div class="chat-input-container">', unsafe_allow_html=True)
    
    # Schema browser first (collapsed by default)
    display_schema_viewer()
    
    # ERD Section with minimal height
    st.subheader("Entity Relationship Diagram")
    with st.spinner("Generating Entity Relationship Diagram..."):
        erd_path, error = get_schema_erd()
        if erd_path:
            # Create columns with wider center for ultra-compact display
            left_col, center_col, right_col = st.columns([1, 4, 1])
            with center_col:
                st.image(erd_path, use_container_width=True)
        else:
            st.error(f"Failed to generate ERD: {error}")
    
    st.divider()
    
    # Chat input and history
    prompt = st.chat_input("Ask a question about your database...")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Scrollable chat history
    st.markdown('<div class="chat-history-container">', unsafe_allow_html=True)
    display_chat_history()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Handle chat input
    if prompt:
        # Display user message
        with st.chat_message("user"):
            st.write(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        # Get and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                result = st.session_state.chatbot.query(prompt)
                
                if result["success"]:
                    # Store response data
                    response_data = {
                        "role": "assistant",
                        "content": result["response"],
                        "sql": result["sql_query"],
                        "data": pd.DataFrame(result["raw_result"])
                    }
                    
                    # Display response
                    st.write(response_data["content"])
                    
                    # Display SQL query
                    with st.expander("🔍 View SQL Query", expanded=False):
                        st.code(response_data["sql"], language="sql")
                    
                    # Display data and visualizations
                    if not response_data["data"].empty:
                        with st.expander("📊 View Data & Visualizations", expanded=False):
                            col1, col2 = st.columns([2, 1])
                            with col1:
                                st.dataframe(
                                    response_data["data"],
                                    use_container_width=True,
                                    hide_index=True
                                )
                            
                            with col2:
                                try:
                                    numeric_cols = response_data["data"].select_dtypes(
                                        include=['float64', 'int64']
                                    ).columns
                                    if len(numeric_cols) >= 1:
                                        fig = px.bar(response_data["data"], 
                                                   x=response_data["data"].columns[0], 
                                                   y=numeric_cols[0],
                                                   title="Data Visualization")
                                        fig.update_layout(
                                            plot_bgcolor='rgba(0,0,0,0)',
                                            paper_bgcolor='rgba(0,0,0,0)',
                                            font=dict(color='white')
                                        )
                                        st.plotly_chart(fig, use_container_width=True)
                                except Exception:
                                    pass
                    
                    # Add to chat history after displaying
                    st.session_state.chat_history.append(response_data)
                else:
                    error_message = f"❌ Error: {result['error']}"
                    st.error(error_message)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": error_message,
                        "data": pd.DataFrame()
                    })
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

        # Create table nodes with enhanced HTML-like labels
        for table, cols in tables.items():
            label = f'''<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="8">
                <TR><TD PORT="header" BGCOLOR="#E0E0E0"><FONT POINT-SIZE="14"><B>{table}</B></FONT></TD></TR>'''
            
            for col in cols:
                label += f'<TR><TD PORT="{col.split()[0]}" ALIGN="LEFT"><FONT POINT-SIZE="12">{col}</FONT></TD></TR>'
            label += '</TABLE>>'
            
            dot.node(table, label=label)

        # Add relationships with improved styling
        for table, column, ref_table, ref_column in relationships:
            dot.edge(
                f"{table}:{column}:e",
                f"{ref_table}:{ref_column}:w",
                dir="both",
                arrowhead="crowodot",
                arrowtail="teedot",
                color="#666666",
                penwidth="1.0"
            )

        dot.render(output_file, cleanup=True, format="png")
        cursor.close()
        conn.close()
        return f"{output_file}.png", None
            
    except Exception as e:
        return None, f"Failed to generate ERD: {str(e)}"
    
if __name__ == "__main__":
    main()