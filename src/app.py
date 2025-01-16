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
import time
import plotly.express as px
from streamlit_lottie import st_lottie
import requests

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
    if 'chatbot' not in st.session_state:
        load_dotenv()
        
        # Add model selection in sidebar
        with st.sidebar:
            llm_provider = st.selectbox(
                "Select LLM Provider",
                ["sambanova", "gemini"],
                help="SambaNova (faster) or Google's Gemini"
            )
            
        with st.spinner('Initializing chatbot...'):
            db_url = os.getenv("DATABASE_URL")
            schema_manager = SchemaManager(db_url)
            
            # Only update vector store if embeddings don't exist
            if not schema_manager.embeddings_exist():
                with st.spinner('Generating schema embeddings...'):
                    schema_manager.update_vector_store()
            
            st.session_state.chatbot = DBChatbot(schema_manager, llm_provider)
    if 'schema_info' not in st.session_state:
        st.session_state.schema_info = st.session_state.chatbot.schema_manager.get_schema_info()

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
    st.set_page_config(
        page_title="Chat with Your Database",
        page_icon="🗄️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    load_css()
    
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
    
    initialize_session_state()
    
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
    prompt = st.chat_input("Ask a question about your database...")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Scrollable chat history
    st.markdown('<div class="chat-history-container">', unsafe_allow_html=True)
    display_schema_viewer()
    st.markdown("<div class='schema-chat-separator'></div>", unsafe_allow_html=True)
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

if __name__ == "__main__":
    main()