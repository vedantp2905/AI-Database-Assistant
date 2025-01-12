from schema_manager import SchemaManager
from dotenv import load_dotenv
import os
import json

def embed_schema():
    # Force reload environment variables
    os.environ.clear()
    load_dotenv(override=True)
    
    # Initialize SchemaManager with your database URL
    db_url = os.getenv("DATABASE_URL")
    print(f"Using database URL: {db_url}")
    schema_manager = SchemaManager(db_url)
    
    # Get and print schema info before embedding
    schema_info = schema_manager.get_schema_info()
    print("\nDatabase Schema:")
    print(json.dumps(schema_info, indent=2))
    
    # Update the vector store with current schema
    schema_manager.update_vector_store()
    print("\nSchema has been embedded successfully!")
    
if __name__ == "__main__":
    embed_schema() 