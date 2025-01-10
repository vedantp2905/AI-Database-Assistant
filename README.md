# Chat with Your Database

A Python-based application that allows you to interact with your database using natural language. Powered by LangChain and Google's Gemini Pro model, this application translates your questions into SQL queries, executes them, and returns the results in a conversational format.

## Features

- **Natural Language to SQL Conversion**: Seamlessly convert your questions into SQL queries.
- **Schema-Aware Query Generation**: Understands your database schema to generate accurate queries.
- **SQL Query Validation**: Ensures security by validating queries before execution.
- **Vector Store-Based Schema Matching**: Efficiently matches your questions to the relevant parts of your schema.
- **Complex Relationship Handling**: Supports intricate database relationships and foreign key management.

## Prerequisites

- Python 3.8+
- MySQL Database
- Google API Key (Gemini Pro access)

## Installation

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd <project-directory>
   ```

2. **Create and Activate a Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. **Create a `.env` File**:
   Add your Google API key and database URL in the `.env` file:
   ```plaintext
   GOOGLE_API_KEY=your_google_api_key
   DATABASE_URL=mysql+mysqlconnector://username:password@localhost:3306/database_name
   ```

2. **Set Up Your MySQL Database**:
   Ensure your MySQL database is running and accessible.

## Project Structure

```
project/
├── src/
│   ├── main.py           # Main application entry point
│   ├── chatbot.py        # Chatbot implementation
│   ├── schema_manager.py # Database schema management
│   ├── sql_validator.py  # SQL query validation
│   └── embed_schema.py   # Schema embedding utility
├── vector_store/         # Local vector store data
├── requirements.txt      # Project dependencies
└── .env                  # Environment variables
```

## Usage

1. **Embed Your Database Schema**:
   Before chatting, embed your schema to help the application understand your database structure.
   ```bash
   python src/embed_schema.py
   ```

2. **Start the Application**:
   Launch the main application to begin interacting with your database.
   ```bash
   python src/main.py
   ```

3. **Chat with Your Database**:
   Ask questions in natural language and receive answers based on your database's data.
   ```plaintext
   Ask a question (or 'quit' to exit): What is the average salary of employees?
   ```

## Example Queries

- "List all departments and their managers."
- "What is the average salary in each department?"
- "Show employees who work in multiple departments."
- "Which department has the highest budget?"

## Security Features

- **SQL Injection Prevention**: Protects against malicious queries.
- **SELECT Queries Only**: Restricts operations to safe, read-only queries.
- **Forbidden Keywords Filtering**: Blocks dangerous SQL keywords.
- **Query Validation**: Ensures queries are safe before execution.

## Limitations

- **SELECT Queries Only**: Currently supports only read operations.
- **Schema Embedding Required**: Must embed schema before use.
- **Local Vector Store**: Not suitable for distributed systems.
- **Manual Schema Updates**: Requires re-embedding after schema changes.

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Commit your changes.
4. Push to the branch.
5. Create a Pull Request.

## License

MIT License

## Acknowledgments

- **LangChain**: For the framework.
- **Google's Gemini Pro**: For natural language processing.
- **Chroma**: For vector store implementation.
