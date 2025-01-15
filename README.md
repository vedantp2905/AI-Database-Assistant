Here's an updated version of the README.md that includes the changes made to the `src/chatbot.py` file, specifically regarding the LLM's behavior to return only the SQL query without any additional text or formatting. I've also added a section about the new critical rules for SQL generation.

```markdown:README.md
# AI Database Assistant

A Python-based application that allows natural language interaction with your database using sentence transformers and Google's Gemini Pro model. This application translates questions into SQL queries, executes them, and returns results in a conversational format.

## Key Features

- **Natural Language to SQL**: Convert questions into SQL queries using Gemini Pro
- **Optimized Schema Understanding**: 
  - Uses BAAI/bge-large-en-v1.5 embeddings
  - Normalized vector similarity search
  - Semantic table matching
  - Efficient batch processing
- **Streamlit Web Interface**: Interactive UI with schema visualization
- **Smart Schema Management**:
  - Automatic schema detection
  - Persistent embeddings storage
  - Optimized similarity search
  - Batch processing for performance
- **Security & Validation**: SQL injection prevention and query validation

## Critical Rules for SQL Generation

1. Use ONLY the exact table and column names shown in the schema.
2. Do not use aliases like 'e' or 'd' unless you define them in proper table aliases.
3. Every column reference must exactly match a column from the schema.
4. Do not guess or assume column names - use only what is explicitly shown.
5. If you can't find an exact column or join path in the schema, respond with 'INVALID_QUERY'.

## Prerequisites

- Python 3.8+
- MySQL Database
- Google API Key (for Gemini Pro)

## Installation

1. **Clone and Setup**:
   ```bash
   git clone <repository-url>
   cd <project-directory>
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   Create a `.env` file:
   ```plaintext
   GOOGLE_API_KEY=your_google_api_key
   SAMBANOVA_API_KEY=your_sambanova_api_key
   DATABASE_URL=mysql+mysqlconnector://username:password@localhost:3306/database_name
   TRANSFORMERS_OFFLINE=1
   SENTENCE_TRANSFORMERS_HOME=./models
   HF_DATASETS_OFFLINE=1
   ```

## Project Structure

```
project/
├── src/
│   ├── main.py           # CLI interface
│   ├── app.py            # Streamlit web interface
│   ├── chatbot.py        # Core chatbot logic
│   ├── schema_manager.py # Schema handling & embeddings
│   ├── sql_validator.py  # Query validation
│   └── embed_schema.py   # Schema embedding utility
├── vector_store/         # Persistent embeddings storage
│   ├── embeddings.npy    # Numpy array embeddings
│   ├── texts.json        # Schema descriptions
│   └── metadata.json     # Table metadata
├── models/              # Local model storage
├── requirements.txt     # Dependencies
└── .env                 # Configuration
```

## Usage

1. **Embed Schema** (Required first time & after database changes):
   ```bash
   python src/embed_schema.py
   ```

2. **Launch Application**:
   - For CLI interface:
     ```bash
     python src/main.py
     ```
   - For web interface:
     ```bash
     streamlit run src/app.py
     ```

## Technical Details

### Embedding System
- Uses BAAI/bge-large-en-v1.5 for high-quality embeddings
- Fallback to all-MiniLM-L6-v2 if needed
- Normalized vectors for efficient similarity search
- Persistent storage of embeddings and metadata
- Batch processing for performance

### Schema Management
- Automatic schema reflection using SQLAlchemy
- Detailed column information including:
  - Data types
  - Primary keys
  - Foreign key relationships
- Semantic table search with configurable thresholds
- Deduplication of search results

### Database Connection
- SQLAlchemy engine with connection pooling
- Support for MySQL via mysql-connector-python
- Connection timeout handling
- Pool recycling for stability

## Security Features

- SQL injection prevention
- Query validation and sanitization
- Read-only operations (SELECT only)
- Forbidden keywords filtering

## Limitations & Known Issues

- SELECT queries only
- Requires schema embedding after changes in the database
- Local vector store (not distributed) can change by using a vector database for distributed processing
- Manual schema updates needed
