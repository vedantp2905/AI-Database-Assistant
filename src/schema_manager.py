import numpy as np
import json
import logging
import os
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, MetaData, text
from typing import List, Dict
from numpy.linalg import norm

class SchemaManager:
    def __init__(self, db_url: str, schema_name: str = None, vector_store_path="./vector_store", model_path="./models"):
        self.db_url = db_url.rstrip('/')  # Remove trailing slash if present
        self.schema_name = schema_name
        self.model_path = model_path
        
        # Create schema-specific vector store path
        if schema_name:
            self.vector_store_path = os.path.join(vector_store_path, schema_name)
            print(f"Using schema-specific vector store path: {self.vector_store_path}")
        else:
            self.vector_store_path = vector_store_path
            print("Using default vector store path (no schema specified)")
            
        os.makedirs(self.vector_store_path, exist_ok=True)
            
        # Schema-specific paths for storing embeddings and metadata
        self.embeddings_file = os.path.join(self.vector_store_path, "embeddings.npy")
        self.texts_file = os.path.join(self.vector_store_path, "texts.json")
        self.metadata_file = os.path.join(self.vector_store_path, "metadata.json")
        
        print(f"Embeddings file: {self.embeddings_file}")
        print(f"Texts file: {self.texts_file}")
        print(f"Metadata file: {self.metadata_file}")
        
        # Initialize storage for schema embeddings
        self.schema_texts = []
        self.schema_embeddings = None
        self.schema_metadata = []
        
        # Initialize database connection
        self._initialize_db_connection()
        
        # Initialize embeddings model
        self._initialize_embeddings_model()
        
        # Load existing embeddings if available and schema hasn't changed
        if self.embeddings_exist():
            if not self._schema_has_changed():
                self._load_stored_data()
                self._normalize_embeddings()
            else:
                print("Schema changes detected, updating embeddings...")
                self.update_vector_store()
        # Otherwise update vector store for schema-specific embeddings
        elif schema_name:
            self.update_vector_store()
        
    def _initialize_db_connection(self):
        """Initialize database connection"""
        try:
            # Create SQLAlchemy engine using the provided database URL
            connect_args = {}
            
            # Add MySQL-specific connection arguments if using mysql connector
            if 'mysql' in self.db_url.lower():
                connect_args = {
                    'pool_recycle': 3600,
                    'pool_timeout': 30,
                    'pool_pre_ping': True
                }
            
            if self.schema_name:
                # Properly construct the database URL with schema
                if '?' in self.db_url:
                    base_url, params = self.db_url.split('?')
                    self.engine_url = f"{base_url}/{self.schema_name}?{params}"
                else:
                    self.engine_url = f"{self.db_url}/{self.schema_name}"
            else:
                self.engine_url = self.db_url
            
            self.engine = create_engine(
                self.engine_url,
                **connect_args
            )
            
            # Test connection
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).fetchone()
                print("Database connection successful!")
                
        except Exception as e:
            logging.error(f"Database connection error: {str(e)}")
            raise ConnectionError(f"Failed to connect to database: {str(e)}")
        
        # Add normalized embeddings cache
        self.normalized_embeddings = None
        self._normalize_embeddings()
    
    def _initialize_embeddings_model(self):
        """Initialize embeddings model"""
        try:
            # Try loading from local path first
            local_model_path = os.path.join(self.model_path, "bge-large-en-v1.5")
            if os.path.exists(local_model_path):
                self.model = SentenceTransformer(local_model_path)
                print("Loaded model from local path")
            else:
                # Fallback to downloading or smaller model
                try:
                    self.model = SentenceTransformer(
                        "BAAI/bge-large-en-v1.5",
                        cache_folder=self.model_path
                    )
                    print("Downloaded model from HuggingFace")
                except Exception as e:
                    print(f"Failed to load BAAI model: {e}")
                    self.model = SentenceTransformer(
                        'all-MiniLM-L6-v2',
                        cache_folder=self.model_path
                    )
                    print("Using fallback model: all-MiniLM-L6-v2")
        
        except Exception as e:
            print(f"Model initialization failed: {e}")
            raise
    
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
            
            print("Loaded existing embeddings and metadata")
        except Exception as e:
            print(f"Could not load stored data: {e}")
    
    def get_schema_info(self):
        """Extract schema information from database"""
        metadata = MetaData()
        metadata.reflect(bind=self.engine)
        
        schema_info = []
        for table in metadata.tables.values():
            table_info = {
                "table_name": table.name,
                "table_description": table.comment,
                "columns": [
                    {
                        "name": column.name,
                        "type": str(column.type),
                        "primary_key": column.primary_key,
                        "column_description": column.comment,
                        "foreign_key": {
                            "is_fk": bool(column.foreign_keys),
                            "references": [
                                {
                                    "table": fk.column.table.name,
                                    "column": fk.column.name,
                                    "column_description": fk.column.comment
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
    
    def _normalize_embeddings(self):
        """Normalize embeddings for faster cosine similarity"""
        if self.schema_embeddings is not None:
            # Normalize embeddings for faster cosine similarity computation
            self.normalized_embeddings = self.schema_embeddings / np.maximum(
                norm(self.schema_embeddings, axis=1, keepdims=True),
                1e-12  # Avoid division by zero
            )
    
    def similarity_search(self, query: str, k: int = 3, threshold: float = 0.5) -> List[Dict]:
        """Optimized similarity search using normalized embeddings"""
        # Encode and normalize query
        query_embedding = self.model.encode([query])[0]
        query_norm = query_embedding / np.maximum(norm(query_embedding), 1e-12)
        
        # Compute similarities using normalized vectors (dot product = cosine similarity)
        similarities = np.dot(self.normalized_embeddings, query_norm)
        
        # Get top k results above threshold
        top_k_indices = np.argsort(similarities)[-k:][::-1]
        top_k_scores = similarities[top_k_indices]
        
        results = []
        for idx, score in zip(top_k_indices, top_k_scores):
            if score < threshold:
                continue
            results.append({
                'content': self.schema_texts[idx],
                'metadata': self.schema_metadata[idx],
                'score': float(score)
            })
        
        return results

    def update_vector_store(self, progress_callback=None):
        """Update schema embeddings with optimization and progress tracking"""
        print("Updating vector store...")
        schema_info = self.get_schema_info()
        self.schema_texts = []
        self.schema_metadata = []
        
        # Batch process descriptions for better performance
        descriptions = []
        total_items = len(schema_info)
        
        for idx, table in enumerate(schema_info):
            # Update progress if callback provided
            if progress_callback:
                progress = (idx / total_items) * 0.5
                progress_callback(progress)
            
            # Process table descriptions
            table_metadata = {
                "table": table['table_name'],
                "type": "table",
                "description": table['table_description'],
                "columns": []
            }
            
            # Add table-level description
            description = f"Table {table['table_name']}"
            if table['table_description']:
                description += f" ({table['table_description']})"
            description += " contains columns: "
            
            # Process columns
            column_descriptions = []
            for col in table['columns']:
                # Add column metadata
                col_metadata = {
                    "name": col['name'],
                    "type": col['type'],
                    "primary_key": col.get('primary_key', False),
                    "foreign_key": col['foreign_key'],
                    "description": col.get('column_description', '')
                }
                table_metadata["columns"].append(col_metadata)
                
                # Build column description
                col_desc = f"{col['name']} ({col['type']})"
                if col['column_description']:
                    col_desc += f" - {col['column_description']}"
                if col['primary_key']:
                    col_desc += " (primary key)"
                if col['foreign_key']['is_fk']:
                    refs = col['foreign_key']['references']
                    ref_descriptions = []
                    for r in refs:
                        ref_desc = f"{r['table']}.{r['column']}"
                        if r['column_description']:
                            ref_desc += f" ({r['column_description']})"
                        ref_descriptions.append(ref_desc)
                    col_desc += f" (foreign key referencing {', '.join(ref_descriptions)})"
                column_descriptions.append(col_desc)
            
            description += ", ".join(column_descriptions)
            descriptions.append(description)
            self.schema_texts.append(description)
            self.schema_metadata.append(table_metadata)
        
        # Batch encode with progress updates
        self.schema_embeddings = self.model.encode(
            descriptions,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        if progress_callback:
            progress_callback(1.0)
        
        # Update normalized embeddings cache
        self._normalize_embeddings()
        
        # Save to files
        self._save_stored_data()

    def semantic_table_search(self, query: str, min_score: float = 0.6) -> List[Dict]:
        """Search for semantically similar tables"""
        results = self.similarity_search(query, k=len(self.schema_texts), threshold=min_score)
        
        # Group by table and aggregate scores
        table_scores = {}
        for result in results:
            table_name = result['metadata']['table']
            score = result['score']
            if table_name not in table_scores or score > table_scores[table_name]['score']:
                table_scores[table_name] = {
                    'table': table_name,
                    'score': score,
                    'description': result['content']
                }
        
        # Sort by score and return results
        return sorted(
            table_scores.values(),
            key=lambda x: x['score'],
            reverse=True
        )

    def embeddings_exist(self) -> bool:
        """Check if embeddings and metadata files exist and are valid"""
        if not os.path.exists(self.embeddings_file) or \
           not os.path.exists(self.texts_file) or \
           not os.path.exists(self.metadata_file):
            return False
        
        try:
            # Quick validation of files
            np.load(self.embeddings_file)
            with open(self.texts_file) as f:
                json.load(f)
            with open(self.metadata_file) as f:
                json.load(f)
            return True
        except Exception:
            return False

    def get_available_schemas(self):
        """Get list of available schemas from database"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SHOW DATABASES"))
                schemas = [row[0] for row in result]
                return [schema for schema in schemas if schema not in ['information_schema', 'mysql', 'performance_schema', 'sys']]
        except Exception as e:
            logging.error(f"Failed to get schemas: {str(e)}")
            return []

    def _schema_has_changed(self) -> bool:
        """Compare current schema metadata with stored metadata"""
        try:
            # Get current schema metadata in the same format as stored
            current_schema = []
            schema_info = self.get_schema_info()
            
            for table in schema_info:
                table_data = {
                    "table": table['table_name'],
                    "type": "table",
                    "description": table['table_description'],
                    "columns": []
                }
                
                for col in table['columns']:
                    col_data = {
                        "name": col['name'],
                        "type": col['type'],
                        "primary_key": col.get('primary_key', False),
                        "foreign_key": {
                            "is_fk": col['foreign_key'].get('is_fk', False),
                            "references": col['foreign_key'].get('references', [])
                        },
                        "description": col.get('column_description')
                    }
                    table_data["columns"].append(col_data)
                
                current_schema.append(table_data)
                
            # Load stored metadata
            if not os.path.exists(self.metadata_file):
                return True
            
            with open(self.metadata_file, 'r') as f:
                stored_metadata = json.load(f)
            
            # Compare the exact JSON structure
            return json.dumps(current_schema, sort_keys=True) != json.dumps(stored_metadata, sort_keys=True)
            
        except Exception as e:
            logging.warning(f"Error comparing schema metadata: {e}")
            return True  # If there's any error, assume schema has changed
