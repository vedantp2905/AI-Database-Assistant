import numpy as np
import json
import logging
import os
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, MetaData, text
from typing import List, Dict
from numpy.linalg import norm

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
            # Create SQLAlchemy engine using the provided database URL
            connect_args = {
                'connect_timeout': 30,
                'pool_recycle': 3600
            }
            
            self.engine = create_engine(
                self.db_url,
                pool_pre_ping=True
            )
            
            # Test connection
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).fetchone()
                logging.info("Database connection successful!")
                
        except Exception as e:
            logging.error(f"Database connection error: {str(e)}")
            raise ConnectionError(f"Failed to connect to database: {str(e)}")
        
        # Add normalized embeddings cache
        self.normalized_embeddings = None
        self._normalize_embeddings()
    
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

    def update_vector_store(self):
        """Update schema embeddings with optimization"""
        schema_info = self.get_schema_info()
        self.schema_texts = []
        self.schema_metadata = []
        
        # Batch process descriptions for better performance
        descriptions = []
        
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
            descriptions.append(description)
            self.schema_texts.append(description)
            self.schema_metadata.append({"table": table['table_name']})
        
        # Batch encode all descriptions at once
        self.schema_embeddings = self.model.encode(
            descriptions,
            batch_size=32,  # Adjust based on your GPU/CPU
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True  # Pre-normalize embeddings
        )
        
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
