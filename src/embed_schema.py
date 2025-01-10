from schema_manager import SchemaManager
from dotenv import load_dotenv
import os
import json

def embed_schema():
    # Load environment variables
    load_dotenv()
    
    # Initialize SchemaManager with your database URL
    db_url = os.getenv("DATABASE_URL")
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