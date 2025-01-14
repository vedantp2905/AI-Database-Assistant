import numpy as np
import json
import logging
import os
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, MetaData, text
import pymysql

class SchemaManager:
    def __init__(self, db_url, vector_store_path="./vector_store", model_path="./models"):
        self.db_url = db_url
        self.model_path = model_path
        self.vector_store_path = vector_store_path
        os.makedirs(self.vector_store_path, exist_ok=True)
        
        # Paths for storing embeddings and metadata
        self.embeddings_file = os.path.join(vector_store_path, "embeddings.npy")
        self.texts_file = os.path.join(vector_store_path, "texts.json")
        self.metadata_file = os.path.join(vector_store_path, "metadata.json")
        
        # Initialize storage for schema embeddings
        self.schema_texts = []
        self.schema_embeddings = None
        self.schema_metadata = []
        
        # Try to load existing embeddings
        self._load_stored_data()
        
        # Initialize embeddings with offline support
        try:
            # Try loading from local path first
            local_model_path = os.path.join(self.model_path, "bge-large-en-v1.5")
            if os.path.exists(local_model_path):
                self.model = SentenceTransformer(local_model_path)
                logging.info("Loaded model from local path")
            else:
                # Fallback to downloading or smaller model
                try:
                    self.model = SentenceTransformer(
                        "BAAI/bge-large-en-v1.5",
                        cache_folder=self.model_path
                    )
                    logging.info("Downloaded model from HuggingFace")
                except Exception as e:
                    logging.warning(f"Failed to load BAAI model: {e}")
                    self.model = SentenceTransformer(
                        'all-MiniLM-L6-v2',
                        cache_folder=self.model_path
                    )
                    logging.info("Using fallback model: all-MiniLM-L6-v2")
        
        except Exception as e:
            logging.error(f"Model initialization failed: {e}")
            raise
        
        try:
            # Hardcoded PyMySQL connection
            timeout = 30
            self.mysql_conn = pymysql.connect(
                charset="utf8mb4",
                connect_timeout=timeout,
                cursorclass=pymysql.cursors.DictCursor,
                db="threetables",
                host="134.209.216.55",
                password="AVNS_NM6xK_jeLt7vvQQAnx7",
                read_timeout=timeout,
                port=27573,
                user="avnadmin",
                write_timeout=timeout
            )
            print("PyMySQL Connection successful!")
            
            # Test PyMySQL connection
            with self.mysql_conn.cursor() as cursor:
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()
                print(f"MySQL Version: {version}")
            
            # Create SQLAlchemy engine
            engine_url = "mysql+pymysql://avnadmin:AVNS_NM6xK_jeLt7vvQQAnx7@134.209.216.55:27573/threetables"
            connect_args = {
                'connect_timeout': timeout,
                'read_timeout': timeout,
                'write_timeout': timeout,
                'charset': 'utf8mb4'
            }
            
            self.engine = create_engine(
                engine_url,
                connect_args=connect_args,
                pool_pre_ping=True,
                pool_recycle=3600
            )
            
            # Test SQLAlchemy connection
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).fetchone()
                print("SQLAlchemy Connection successful!")
                
        except Exception as e:
            print(f"Detailed error: {str(e)}")
            print(f"Error type: {type(e)}")
            if hasattr(e, 'args') and len(e.args) > 1:
                print(f"Error code: {e.args[0]}")
                print(f"Error message: {e.args[1]}")
            raise ConnectionError(f"Failed to connect to database: {str(e)}")
        
    def _save_stored_data(self):
        """Save embeddings and metadata to files"""
        if self.schema_embeddings is not None:
            np.save(self.embeddings_file, self.schema_embeddings)
        
        with open(self.texts_file, 'w') as f:
            json.dump(self.schema_texts, f)
        
        with open(self.metadata_file, 'w') as f:
            json.dump(self.schema_metadata, f)
    
    def _load_stored_data(self):
        """Load embeddings and metadata from files"""
        try:
            if os.path.exists(self.embeddings_file):
                self.schema_embeddings = np.load(self.embeddings_file)
            
            if os.path.exists(self.texts_file):
                with open(self.texts_file) as f:
                    self.schema_texts = json.load(f)
            
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file) as f:
                    self.schema_metadata = json.load(f)
            
            logging.info("Loaded existing embeddings and metadata")
        except Exception as e:
            logging.warning(f"Could not load stored data: {e}")
    
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
    
    def similarity_search(self, query, k=3):
        """Perform similarity search using sentence transformers directly"""
        query_embedding = self.model.encode([query])[0]
        
        # Calculate cosine similarity
        similarities = np.dot(self.schema_embeddings, query_embedding) / (
            np.linalg.norm(self.schema_embeddings, axis=1) * np.linalg.norm(query_embedding)
        )
        
        # Get top k results
        top_k_indices = np.argsort(similarities)[-k:][::-1]
        
        results = []
        for idx in top_k_indices:
            results.append({
                'content': self.schema_texts[idx],
                'metadata': self.schema_metadata[idx]
            })
            
        return results

    def update_vector_store(self):
        """Update schema embeddings"""
        schema_info = self.get_schema_info()
        self.schema_texts = []
        self.schema_metadata = []
        
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
            self.schema_texts.append(description)
            self.schema_metadata.append({"table": table['table_name']})
        
        # Create embeddings
        self.schema_embeddings = self.model.encode(self.schema_texts)
        
        # Save to files
        self._save_stored_data()
