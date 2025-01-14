import os
from dotenv import load_dotenv
from schema_manager import SchemaManager
from chatbot import DBChatbot

def main():
    load_dotenv()
    
    # Initialize SchemaManager
    db_url = os.getenv("DATABASE_URL")
    schema_manager = SchemaManager(db_url)
    
    # Only update vector store if embeddings don't exist
    if not schema_manager.embeddings_exist():
        print("Generating schema embeddings...")
        schema_manager.update_vector_store()
    
    # Initialize chatbot
    chatbot = DBChatbot(schema_manager)
    
    # Example usage
    while True:
        question = input("Ask a question (or 'quit' to exit): ")
        if question.lower() == 'quit':
            break
            
        result = chatbot.query(question)
        if result["success"]:
            print("\nResponse:", result["response"])
            print("\nSQL Query:", result["sql_query"])
        else:
            print("\nError:", result["error"])

if __name__ == "__main__":
    main() 