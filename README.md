# AI Database Assistant

An intelligent database management system that combines natural language processing with advanced schema management to make database operations accessible to everyone.

## Why This Matters

### 1. Database Design & Management
- **Natural Language Schema Design**: Create and modify database schemas using plain English
- **Intelligent Schema Evolution**: AI-powered suggestions for schema improvements
- **Automated Relationship Detection**: Smart foreign key and relationship management
- **Schema Version Control**: Track and manage schema changes over time

### 2. Data Exploration
- **Natural Language Queries**: Convert English questions to SQL
- **Context-Aware Responses**: Maintains conversation context for follow-up questions
- **Smart Schema Understanding**: Uses embeddings to find relevant tables and relationships
- **Automatic Visualizations**: Generates charts and graphs from query results

### 3. Multi-Schema Support
- **Schema Isolation**: Separate vector stores for each database schema
- **Schema-Specific Embeddings**: Optimized embeddings for each database
- **Cross-Schema Analytics**: Query across multiple schemas when needed
- **Schema Migration Tools**: Easy database creation and modification

## Key Features

### Database Builder
- Natural language schema creation
- Entity relationship modeling
- Automated foreign key detection
- Schema visualization
- Change history tracking
- Schema validation

### Query Interface
- Natural language to SQL conversion
- Context-aware query generation
- Automatic data visualization
- Query validation and safety checks
- Result formatting and explanation

### Schema Management
- Schema-specific vector stores
- Automatic embedding updates
- Schema change detection
- Version control
- Migration management

## Project Structure

```
project/
├── src/
│   ├── query_app.py              # Streamlit web interface
│   ├── chatbot.py          # Query processing & NL responses
│   ├── embed_schema.py     # Schema embedding utility
│   ├── llm_factory.py      # LLM provider management
│   ├── main.py            # CLI interface
│   ├── schema_app.py      # Schema management interface
│   ├── schema_assistant.py # Schema building assistant
│   ├── schema_designer.py  # Database schema operations
│   ├── schema_history.py   # Schema version control
│   ├── schema_manager.py   # Schema & embedding handling
│   └── sql_validator.py    # Query validation
├── vector_store/
│   └── {schema_name}/      # Schema-specific embeddings
├── schema_history/         # Schema version history
├── models/                 # Local model storage
└── .env                    # Configuration
```

## Installation

1. **Setup Environment**:
```bash
git clone <repository-url>
cd <project-directory>
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Download Embedding Models**:
```bash
python download.py
```
3. **Download graphviz**:

Use the following link to download graphviz:
https://graphviz.org/download/

Add to your PATH while installing

Restart your terminal

4. **Configure Environment**:

Create a .env file in the root directory with the following variables:

```plaintext
GOOGLE_API_KEY=your_api_key
SAMBANOVA_API_KEY=your_api_key
DATABASE_URL=mysql+mysqlconnector://user:pass@localhost:3306/
TRANSFORMERS_OFFLINE=1
SENTENCE_TRANSFORMERS_HOME=./models
HF_DATASETS_OFFLINE=1
```

## Usage

### 1. Database Builder
```bash
streamlit run src/schema_app.py --server.port 8501
```
- Create new databases
- Design schemas using natural language
- Visualize database structure
- Track schema changes
- Redirect to the query interface

### 2. Query Interface
```bash
streamlit run src/query_app.py --server.port 8502
```
- Ask questions in natural language
- View SQL translations
- See data visualizations
- Explore schema relationships

### 3. CLI Interface
```bash
python src/main.py
```
- Quick database queries
- Schema management
- Embedding updates

## Technical Details

### Embedding System
- Primary: BAAI/bge-large-en-v1.5 (1.5B parameters, optimized for semantic search)
- Fallback: all-MiniLM-L6-v2 (384-dimensional embeddings, lightweight alternative)
- Schema-specific vector stores using Chroma DB for efficient similarity search
- Automatic updates triggered on schema changes with versioning
- Normalized vectors using L2 normalization for consistent similarity scores
- Offline model support with local caching for reliability
- Configurable embedding dimensions and batch processing

### LLM Integration
- Google's Gemini Pro with advanced context handling
- SambaNova (optional) for specialized enterprise deployments
- Context-aware prompting with dynamic template generation
- Schema-aware responses with type validation
- Streaming response support for real-time interaction
- Automatic prompt optimization based on query patterns
- Multi-model fallback pipeline for reliability

### Database Support
- MySQL (primary) with full ACID compliance
- SQLAlchemy ORM with connection lifecycle management
- Advanced connection pooling with QueuePool configuration
- Robust transaction management with automatic rollback
- Query optimization and execution planning
- Support for complex joins and subqueries
- Schema versioning and migration tracking

## Security

- Comprehensive SQL injection prevention using parameterized queries
- Multi-layer query validation and sanitization
- Strictly enforced read-only operations for safety
- Schema-level isolation with separate vector stores
- Role-based access control with granular permissions
- Input validation and output encoding
- Secure connection handling with SSL/TLS
- Query rate limiting and timeout controls
