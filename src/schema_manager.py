from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from sqlalchemy import create_engine, MetaData
import google.generativeai as genai
import os

class SchemaManager:
    def __init__(self, db_url, vector_store_path="./vector_store"):
        self.db_url = db_url
        self.vector_store_path = vector_store_path
        
        # Initialize Google API
        genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        
        self.vector_store = None
        self.engine = create_engine(db_url)
        
    def get_schema_info(self):
        """Extract schema information from database"""
        metadata = MetaData()
        metadata.reflect(bind=self.engine)
        
        schema_info = []
        for table in metadata.tables.values():
            table_info = {
                "table_name": table.name,
                "columns": [
                    {
                        "name": column.name,
                        "type": str(column.type),
                        "primary_key": column.primary_key,
                        "foreign_key": {
                            "is_fk": bool(column.foreign_keys),
                            "references": [
                                {
                                    "table": fk.column.table.name,
                                    "column": fk.column.name
                                }
                                for fk in column.foreign_keys
                            ] if column.foreign_keys else []
                        }
                    }
                    for column in table.columns
                ]
            }
            schema_info.append(table_info)
        return schema_info
    
    def update_vector_store(self):
        """Update vector store with current schema information"""
        schema_info = self.get_schema_info()
        texts = []
        metadatas = []
        
        for table in schema_info:
            description = f"Table {table['table_name']} contains columns: "
            column_descriptions = []
            
            for col in table['columns']:
                col_desc = f"{col['name']} ({col['type']})"
                if col['primary_key']:
                    col_desc += " (primary key)"
                if col['foreign_key']['is_fk']:
                    refs = col['foreign_key']['references']
                    ref_desc = ", ".join([f"{r['table']}.{r['column']}" for r in refs])
                    col_desc += f" (foreign key referencing {ref_desc})"
                column_descriptions.append(col_desc)
            
            description += ", ".join(column_descriptions)
            texts.append(description)
            metadatas.append({"table": table['table_name']})
        
        self.vector_store = Chroma.from_texts(
            texts=texts,
            metadatas=metadatas,
            embedding=self.embeddings,
            persist_directory=self.vector_store_path
        )