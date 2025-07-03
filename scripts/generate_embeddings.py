import os
import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
import re

# Configuration
MODEL_NAME = "all-MiniLM-L6-v2"  # Small, fast embedding model
TEXTS_DIR = "data/texts/tripitaka/mn"
EMBEDDINGS_DIR = "data/embeddings/tripitaka/mn"
CHUNK_SIZE = 512  # Maximum tokens per chunk
CHUNK_OVERLAP = 50  # Overlap between chunks

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

def process_text_files():
    """Process all text files and generate embeddings"""
    
    # Load the embedding model
    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    
    # Create embeddings directory
    os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
    
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
                # Save embeddings as numpy array
                output_file = Path(EMBEDDINGS_DIR) / f"{text_file.stem}.npy"
                np.save(output_file, embeddings)
                
                # Save chunks as text file for reference
                chunks_file = Path(EMBEDDINGS_DIR) / f"{text_file.stem}_chunks.txt"
                with open(chunks_file, 'w', encoding='utf-8') as f:
                    for i, chunk in enumerate(chunks):
                        f.write(f"=== CHUNK {i+1} ===\n")
                        f.write(chunk)
                        f.write("\n\n")
                
                # Save metadata
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
                metadata_file = Path(EMBEDDINGS_DIR) / f"{text_file.stem}_metadata.json"
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
                
                print(f"✓ Saved embeddings for {text_file.name} ({len(chunks)} chunks, dim: {embeddings.shape[1]})")
            else:
                print(f"✗ Failed to get embeddings for {text_file.name}")
                
        except Exception as e:
            print(f"Error processing {text_file.name}: {e}")
    
    print(f"\nEmbedding generation complete! Check {EMBEDDINGS_DIR} for results.")

if __name__ == "__main__":
    print(f"Using model: {MODEL_NAME}")
    print(f"Chunk size: {CHUNK_SIZE} characters")
    print(f"Chunk overlap: {CHUNK_OVERLAP} characters")
    
    process_text_files() 