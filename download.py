from transformers import AutoModel, AutoTokenizer
from sentence_transformers import SentenceTransformer
import os

# Set the cache directory
cache_dir = "./models"
os.makedirs(cache_dir, exist_ok=True)

# Download the model and tokenizer
model_name = "BAAI/bge-large-en-v1.5"
model = SentenceTransformer(model_name, cache_folder=cache_dir)

# Save the model
model.save(f"{cache_dir}/bge-large-en-v1.5")

model_name = "all-MiniLM-L6-v2"
model = SentenceTransformer(model_name, cache_folder=cache_dir)

# Save the model
model.save(f"{cache_dir}/all-MiniLM-L6-v2")