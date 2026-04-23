import os
import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import re
import uuid

# Configuration
MODEL_NAME = "all-MiniLM-L6-v2"  # Small, fast embedding model
TEXTS_DIR = "../data/texts/tripitaka/mn"
COLLECTION_NAME = "buddhist_texts_mn"
CHUNK_SIZE = 512  # Maximum tokens per chunk
CHUNK_OVERLAP = 50  # Overlap between chunks

# Qdrant configuration
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333

def split_text_into_chunks(text, max_length=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping chunks"""
    # Clean and normalize text
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Split into sentences first (rough approximation)
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        # If adding this sentence would exceed max_length
        if len(current_chunk + " " + sentence) > max_length and current_chunk:
            chunks.append(current_chunk.strip())
            # Start new chunk with overlap
            words = current_chunk.split()
            overlap_words = words[-overlap:] if len(words) > overlap else words
            current_chunk = " ".join(overlap_words) + " " + sentence
        else:
            current_chunk += " " + sentence if current_chunk else sentence
    
    # Add the last chunk if it exists
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks

def get_embeddings(text_chunks, model):
    """Get embeddings for multiple text chunks"""
    try:
        embeddings = model.encode(text_chunks, convert_to_numpy=True)
        return embeddings
    except Exception as e:
        print(f"Error getting embeddings: {e}")
        return None

def setup_qdrant_collection(client, collection_name, vector_size):
    """Setup Qdrant collection with proper configuration"""
    try:
        # Check if collection exists
        collections = client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        if collection_name in collection_names:
            print(f"Collection '{collection_name}' already exists")
            return True
        else:
            # Create new collection
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )
            print(f"Created collection '{collection_name}' with vector size {vector_size}")
            return True
    except Exception as e:
        print(f"Error setting up Qdrant collection: {e}")
        return False

def store_embeddings_in_qdrant(client, collection_name, embeddings, chunks, metadata):
    """Store embeddings and metadata in Qdrant"""
    try:
        points = []
        for i, (embedding, chunk) in enumerate(zip(embeddings, chunks)):
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding.tolist(),
                payload={
                    "text": chunk,
                    "chunk_id": i,
                    "filename": metadata["filename"],
                    "original_text_length": metadata["original_text_length"],
                    "chunk_size": metadata["chunk_size"],
                    "chunk_overlap": metadata["chunk_overlap"],
                    "model": metadata["model"],
                    "chunk_length": len(chunk)
                }
            )
            points.append(point)
        
        # Upload points to Qdrant
        client.upsert(
            collection_name=collection_name,
            points=points
        )
        
        print(f"✓ Stored {len(points)} embeddings in Qdrant collection '{collection_name}'")
        return True
    except Exception as e:
        print(f"Error storing embeddings in Qdrant: {e}")
        return False

def process_text_files():
    """Process all text files and generate embeddings"""
    
    # Initialize Qdrant client
    print(f"Connecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    # Load the embedding model
    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    
    # Get all text files
    texts_path = Path(TEXTS_DIR)
    text_files = list(texts_path.glob("*.txt"))
    
    print(f"Found {len(text_files)} text files to process")
    
    # Process each file
    for text_file in text_files:
        print(f"Processing {text_file.name}...")
        
        # Read text content
        try:
            with open(text_file, 'r', encoding='utf-8') as f:
                text_content = f.read().strip()
            
            # Skip empty files or files with placeholder content
            if not text_content or text_content == '[No <div class="chapter"> found]':
                print(f"Skipping {text_file.name} - empty or no chapter content")
                continue
            
            # Split text into chunks
            chunks = split_text_into_chunks(text_content)
            print(f"  Split into {len(chunks)} chunks")
            
            # Get embeddings for all chunks
            embeddings = get_embeddings(chunks, model)
            
            if embeddings is not None:
                # Setup Qdrant collection if this is the first file
                if text_file == text_files[0]:
                    if not setup_qdrant_collection(client, COLLECTION_NAME, embeddings.shape[1]):
                        print("Failed to setup Qdrant collection. Exiting.")
                        return
                
                # Prepare metadata
                metadata = {
                    "filename": text_file.name,
                    "original_text_length": len(text_content),
                    "num_chunks": len(chunks),
                    "chunk_size": CHUNK_SIZE,
                    "chunk_overlap": CHUNK_OVERLAP,
                    "embedding_dimension": embeddings.shape[1],
                    "model": MODEL_NAME,
                    "chunk_lengths": [len(chunk) for chunk in chunks]
                }
                
                # Store embeddings in Qdrant
                success = store_embeddings_in_qdrant(client, COLLECTION_NAME, embeddings, chunks, metadata)
                
                if success:
                    print(f"✓ Processed {text_file.name} ({len(chunks)} chunks, dim: {embeddings.shape[1]})")
                else:
                    print(f"✗ Failed to store embeddings for {text_file.name}")
            else:
                print(f"✗ Failed to get embeddings for {text_file.name}")
                
        except Exception as e:
            print(f"Error processing {text_file.name}: {e}")
    
    # Print collection statistics
    try:
        collection_info = client.get_collection(COLLECTION_NAME)
        print(f"\nCollection '{COLLECTION_NAME}' statistics:")
        print(f"  Vector count: {collection_info.points_count}")
    except Exception as e:
        print(f"Error getting collection info: {e}")
    
    print(f"\nEmbedding generation complete! Check Qdrant collection '{COLLECTION_NAME}' for results.")

if __name__ == "__main__":
    print(f"Using model: {MODEL_NAME}")
    print(f"Chunk size: {CHUNK_SIZE} characters")
    print(f"Chunk overlap: {CHUNK_OVERLAP} characters")
    print(f"Qdrant collection: {COLLECTION_NAME}")
    
    process_text_files() 