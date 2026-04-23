import re
import json
from pathlib import Path
from tqdm import tqdm
import nltk
from nltk.tokenize import sent_tokenize
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import tiktoken

nltk.download('punkt')

# === Config ===
INPUT_FILE = "../data/books/breath_cleaned.txt"
OUTPUT_FILE = "../data/books/breath_semantic_chunks.jsonl"
MAX_TOKENS = 800
SIMILARITY_THRESHOLD = 0.7
ENCODING = "cl100k_base"

# Load tokenizer
tokenizer = tiktoken.get_encoding(ENCODING)

def count_tokens(text):
    return len(tokenizer.encode(text))

def split_long_paragraph(paragraph, max_tokens):
    sentences = sent_tokenize(paragraph)
    chunks = []
    current = ""
    for sent in sentences:
        temp = current + " " + sent if current else sent
        if count_tokens(temp) <= max_tokens:
            current = temp
        else:
            if current:
                chunks.append(current.strip())
            current = sent
    if current:
        chunks.append(current.strip())
    return chunks

def clean_text(text):
    text = re.sub(r"\n{0,2}\d+\n{0,2}", "\n", text)  # Remove page numbers
    text = re.sub(r"\n\s*\n\s*", "\n\n", text.strip())  # Paragraph boundaries
    text = re.sub(r'(?<![\.\?!:])\n(?=\w)', ' ', text)  # Join broken lines
    return text.strip()

def semantic_chunking(paragraphs, max_tokens, similarity_threshold, model):
    embeddings = [model.encode(p) for p in tqdm(paragraphs, desc="Encoding paragraphs")]

    chunks = []
    current_chunk = []
    current_tokens = 0
    start_idx = 0
    chunk_id = 1

    i = 0
    while i < len(paragraphs):
        para = paragraphs[i]
        emb = embeddings[i]
        para_tokens = count_tokens(para)

        # Split if paragraph is too long
        if para_tokens > max_tokens:
            split_paras = split_long_paragraph(para, max_tokens)
            split_embeddings = [model.encode(sp) for sp in split_paras]
        else:
            split_paras = [para]
            split_embeddings = [emb]

        for j, sp in enumerate(split_paras):
            sp_tokens = count_tokens(sp)
            sp_emb = split_embeddings[j]

            if current_chunk:
                last_emb = model.encode(current_chunk[-1])
                sim = cosine_similarity([sp_emb], [last_emb])[0][0]
            else:
                sim = 1.0

            if sim >= similarity_threshold and (current_tokens + sp_tokens) <= max_tokens:
                current_chunk.append(sp)
                current_tokens += sp_tokens
            else:
                if current_chunk:
                    chunk_text = "\n\n".join(current_chunk).strip()
                    chunks.append({
                        "id": f"chunk_{chunk_id:04}",
                        "text": chunk_text,
                        "tokens": current_tokens,
                        "start_paragraph": start_idx,
                        "end_paragraph": i - 1
                    })
                    chunk_id += 1
                current_chunk = [sp]
                current_tokens = sp_tokens
                start_idx = i

        i += 1

    if current_chunk:
        chunk_text = "\n\n".join(current_chunk).strip()
        chunks.append({
            "id": f"chunk_{chunk_id:04}",
            "text": chunk_text,
            "tokens": current_tokens,
            "start_paragraph": start_idx,
            "end_paragraph": len(paragraphs) - 1
        })

    return chunks

def main():
    print("📖 Loading and cleaning text...")
    raw_text = Path(INPUT_FILE).read_text(encoding="utf-8")
    cleaned_text = clean_text(raw_text)
    paragraphs = [p.strip() for p in cleaned_text.split("\n\n") if p.strip()]

    print(f"✂️ Number of paragraphs: {len(paragraphs)}")

    print("🧠 Loading embedding model...")
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    print("🔗 Creating semantic chunks...")
    chunks = semantic_chunking(paragraphs, MAX_TOKENS, SIMILARITY_THRESHOLD, model)

    print(f"💾 Saving {len(chunks)} chunks to {OUTPUT_FILE} ...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for chunk in chunks:
            json.dump(chunk, f, ensure_ascii=False)
            f.write("\n")

    print("✅ Done!")

if __name__ == "__main__":
    main()
