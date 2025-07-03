#!/usr/bin/env python3
"""
RAG System for Buddhist Texts

This script implements a Retrieval-Augmented Generation (RAG) system that:
1. Uses sentence-transformers to embed user queries
2. Retrieves the most similar text chunks from the Buddhist texts
3. Generates responses using Ollama with the retrieved context
"""

import os
import json
import numpy as np
import requests
from pathlib import Path
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Tuple
import time

# Configuration
EMBEDDINGS_DIR = "data/embeddings/tripitaka/mn"
TEXTS_DIR = "data/texts/tripitaka/mn"
OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "mistral"  # Change this to your specific model
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TOP_K = 3  # Number of most similar chunks to retrieve

def load_embeddings_and_texts():
    """Load all embeddings and their corresponding texts"""
    embeddings = []
    texts = []
    metadata = []
    
    # Load embedding model for query encoding
    print("Loading embedding model...")
    embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    
    # Iterate through all embedding files
    print("Loading embeddings and texts...")
    for embedding_file in Path(EMBEDDINGS_DIR).glob("*.npy"):
        # Load embedding
        embedding = np.load(embedding_file)
        
        # Load corresponding metadata
        metadata_file = embedding_file.with_suffix('.json')
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                meta = json.load(f)
        else:
            meta = {"filename": embedding_file.stem, "chunk_id": 0}
        
        # Load corresponding text
        text_file = Path(TEXTS_DIR) / f"{meta['filename']}.txt"
        if text_file.exists():
            with open(text_file, 'r', encoding='utf-8') as f:
                text_content = f.read()
        else:
            text_content = f"Text from {meta['filename']}"
        
        embeddings.append(embedding)
        texts.append(text_content)
        metadata.append(meta)
    
    return np.array(embeddings), texts, metadata, embedding_model

def find_similar_chunks(query: str, embeddings, texts, metadata, embedding_model, top_k: int = TOP_K):
    """Find the most similar text chunks to the query"""
    # Encode the query
    query_embedding = embedding_model.encode([query])
    
    # Calculate cosine similarities
    similarities = np.dot(embeddings, query_embedding.T).flatten()
    
    # Get top-k indices
    top_indices = np.argsort(similarities)[::-1][:top_k]
    
    results = []
    for idx in top_indices:
        results.append((
            texts[idx],
            similarities[idx],
            metadata[idx]
        ))
    
    return results

def generate_response_with_ollama(query: str, context: str) -> str:
    """Generate a response using Ollama with the provided context"""
    url = f"{OLLAMA_BASE_URL}/api/generate"
    
    # Create a prompt that includes the context
    prompt = f"""Based on the following Buddhist text context, please answer the question.

Context:
{context}

Question: {query}

Please provide a thoughtful and accurate response based on the context provided:"""
    
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return result.get('response', 'No response generated')
    
    except requests.exceptions.RequestException as e:
        return f"Error communicating with Ollama: {str(e)}"
    except Exception as e:
        return f"Error generating response: {str(e)}"

def rag_query(query: str, embeddings, texts, metadata, embedding_model, top_k: int = TOP_K) -> Dict:
    """Complete RAG pipeline: retrieve relevant texts and generate response"""
    print(f"Query: {query}")
    print("-" * 50)
    
    # Step 1: Find similar chunks
    print("Searching for relevant texts...")
    similar_chunks = find_similar_chunks(query, embeddings, texts, metadata, embedding_model, top_k)
    
    # Step 2: Display retrieved chunks
    print(f"\nRetrieved {len(similar_chunks)} relevant chunks:")
    for i, (text, similarity, meta) in enumerate(similar_chunks, 1):
        print(f"\n--- Chunk {i} (Similarity: {similarity:.4f}) ---")
        print(f"Source: {meta.get('filename', 'Unknown')}")
        print(f"Text: {text[:200]}...")
    
    # Step 3: Combine context
    context = "\n\n".join([text for text, _, _ in similar_chunks])
    
    # Step 4: Generate response
    print("\nGenerating response with Ollama...")
    response = generate_response_with_ollama(query, context)
    
    return {
        "query": query,
        "retrieved_chunks": similar_chunks,
        "response": response,
        "context": context
    }

def interactive_rag():
    """Interactive interface for asking questions"""
    print("Buddhist Texts RAG System")
    print("Type 'quit' to exit")
    print("-" * 40)
    
    # Load data
    embeddings, texts, metadata, embedding_model = load_embeddings_and_texts()
    print(f"Loaded {len(embeddings)} embeddings")
    print(f"Embedding dimension: {embeddings.shape[1]}")
    
    while True:
        query = input("\nEnter your question: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        if not query:
            continue
        
        try:
            result = rag_query(query, embeddings, texts, metadata, embedding_model)
            print("\n" + "="*60)
            print("RESPONSE:")
            print("="*60)
            print(result['response'])
            print("="*60)
        except Exception as e:
            print(f"Error: {str(e)}")

def test_rag():
    """Test the RAG system with a sample query"""
    # Load data
    embeddings, texts, metadata, embedding_model = load_embeddings_and_texts()
    print(f"Loaded {len(embeddings)} embeddings")
    print(f"Embedding dimension: {embeddings.shape[1]}")
    
    # Test query
    test_query = "What does the Buddha teach about mindfulness?"
    result = rag_query(test_query, embeddings, texts, metadata, embedding_model)
    
    print("\n" + "="*60)
    print("FINAL RESPONSE:")
    print("="*60)
    print(result['response'])

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        interactive_rag()
    else:
        test_rag() 