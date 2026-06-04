import os

_chroma = None
_embedder = None

def get_chroma_client() -> "PersistentClient":
    """
    Lazily initializes and returns the ChromaDB persistent client.
    """
    global _chroma
    if _chroma is None:
        from chromadb import PersistentClient
        path = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
        # Ensure directories exist
        os.makedirs(path, exist_ok=True)
        _chroma = PersistentClient(path=path)
    return _chroma

def get_embeddings_api(texts: list[str]) -> tuple[list[list[float]] | None, str | None]:
    """
    Tries to generate embeddings using the Hugging Face Router/Inference API.
    If that fails, falls back to a pure Python TF-IDF hashing vectorizer to avoid memory issues.
    Returns (embeddings, error_message).
    """
    import os
    import math
    import hashlib
    import re
    import httpx
    
    # 1. Hugging Face Router URL Configuration
    model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2").strip()
    if "/" not in model_name:
        model_path = f"sentence-transformers/{model_name}"
    else:
        model_path = model_name
        
    router_url = f"https://router.huggingface.co/hf-inference/pipeline/feature-extraction/{model_path}"
    
    data = {"inputs": texts}
    headers = {"Content-Type": "application/json"}
    
    hf_token = os.getenv("HF_TOKEN")
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token.strip()}"
        
    print(f"Attempting Hugging Face Router API: {router_url}")
    print(f"HF_TOKEN Present = {bool(hf_token)}")
    
    try:
        # Create a transport to force IPv4 connection (binding to 0.0.0.0 forces IPv4 socket resolution)
        transport = httpx.HTTPTransport(local_address="0.0.0.0")
        with httpx.Client(transport=transport, timeout=10.0) as client:
            resp = client.post(router_url, json=data, headers=headers)
            if resp.status_code == 200:
                res = resp.json()
                if isinstance(res, list):
                    # Case 1: 3D list [num_texts, seq_len, embedding_dim]
                    # Mean-pool (average) along the seq_len dimension to get a 2D list [num_texts, embedding_dim]
                    if len(res) > 0 and isinstance(res[0], list) and len(res[0]) > 0 and isinstance(res[0][0], list):
                        pooled_res = []
                        for text_emb in res:
                            seq_len = len(text_emb)
                            dim = len(text_emb[0])
                            mean_vector = [0.0] * dim
                            for token_emb in text_emb:
                                for i in range(dim):
                                    mean_vector[i] += token_emb[i]
                            mean_vector = [val / seq_len for val in mean_vector]
                            # L2 normalize
                            norm = math.sqrt(sum(val ** 2 for val in mean_vector))
                            if norm > 0:
                                mean_vector = [val / norm for val in mean_vector]
                            pooled_res.append(mean_vector)
                        if len(pooled_res) == len(texts):
                            print("Successfully generated and mean-pooled embeddings from HF Router API.")
                            return pooled_res, None
                            
                    # Case 2: 2D list [num_texts, embedding_dim]
                    elif len(res) == len(texts) and all(isinstance(r, list) for r in res):
                        print("Successfully generated 2D embeddings from HF Router API.")
                        return res, None
                        
                    # Case 3: 1D list [embedding_dim] when len(texts) == 1
                    elif len(texts) == 1 and all(isinstance(r, (int, float)) for r in res):
                        print("Successfully generated 1D embedding from HF Router API.")
                        return [res], None
            print(f"HF Router API failed with status {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"HF Router API request failed: {str(e)}")
        
    # 2. Fallback: Pure Python TF-IDF hashing vectorizer to match 384 dimensions
    print("Hugging Face API failed. Falling back to pure Python TF-IDF vectorizer (384 dimensions) to prevent local OOM...")
    
    dimension = 384
    tokenized_texts = []
    for text in texts:
        words = re.findall(r'\b\w+\b', text.lower())
        tokenized_texts.append(words)
        
    num_docs = len(texts)
    word_df = {}
    for words in tokenized_texts:
        for word in set(words):
            word_df[word] = word_df.get(word, 0) + 1
            
    embeddings = []
    for words in tokenized_texts:
        if not words:
            embeddings.append([0.0] * dimension)
            continue
            
        tf = {}
        for word in words:
            tf[word] = tf.get(word, 0) + 1
            
        vector = [0.0] * dimension
        for word, count in tf.items():
            tf_val = count / len(words)
            df_val = word_df.get(word, 0)
            idf_val = math.log((1 + num_docs) / (1 + df_val)) + 1.0
            tfidf = tf_val * idf_val
            
            # Deterministic hash to map word to vector index
            bucket = int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16) % dimension
            vector[bucket] += tfidf
            
        # L2 Normalize
        norm = math.sqrt(sum(val ** 2 for val in vector))
        if norm > 0:
            vector = [val / norm for val in vector]
            
        embeddings.append(vector)
        
    return embeddings, None


def get_embedder() -> "SentenceTransformer":
    """
    Lazily initializes and returns the sentence-transformers model.
    """
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        print("Loading embedding model...")
        _embedder = SentenceTransformer(model_name)
    return _embedder

def check_embedding_fallback(operation_name: str, hf_error: str = None):
    """
    Checks if local SentenceTransformer fallback is disabled to prevent OOM crash.
    """
    if os.getenv("RENDER") or os.getenv("DISABLE_LOCAL_EMBEDDING", "false").lower() == "true":
        err_msg = (
            f"Hugging Face Inference API request failed during {operation_name}. "
            "Local SentenceTransformer fallback is disabled on Render/constrained environments to prevent Out-Of-Memory (OOM) crashes. "
            "Please configure a valid 'HF_TOKEN' environment variable in your Render service settings."
        )
        if hf_error:
            err_msg += f" Details from Hugging Face: {hf_error}"
        raise RuntimeError(err_msg)

def embed_chunks(chunks: list[str], collection_name: str, metadata_list: list[dict]):
    """
    Embeds raw text chunks and uploads them to a specific ChromaDB collection.
    """
    if not chunks:
        return
        
    chroma = get_chroma_client()
    
    # Try Hugging Face Inference API first to save memory (especially on Render Free Tier)
    embeddings, hf_error = get_embeddings_api(chunks)
    
    if embeddings is None:
        check_embedding_fallback("document chunk embedding", hf_error)
        print("Falling back to local SentenceTransformer for embedding...")
        embedder = get_embedder()
        embeddings = embedder.encode(chunks).tolist()
        
    collection = chroma.get_or_create_collection(collection_name)
    
    # Generate unique IDs using doc_type to avoid collisions between documents
    ids = []
    for i, meta in enumerate(metadata_list):
        doc_type = meta.get("doc_type", "doc")
        ids.append(f"{collection_name}_{doc_type}_{i}")
        
    collection.add(documents=chunks, embeddings=embeddings, metadatas=metadata_list, ids=ids)

def hybrid_search(collection_name: str, query: str, n_results: int = 5, where: dict = None) -> list[str]:
    """
    Searches ChromaDB using query embeddings.
    """
    chroma = get_chroma_client()
    
    # Try Hugging Face Inference API first to save memory (especially on Render Free Tier)
    embeddings, hf_error = get_embeddings_api([query])
    
    if embeddings is None:
        check_embedding_fallback("query embedding search", hf_error)
        print("Falling back to local SentenceTransformer for query embedding...")
        embedder = get_embedder()
        query_embedding = embedder.encode([query]).tolist()
    else:
        query_embedding = embeddings
        
    collection = chroma.get_or_create_collection(collection_name)
    
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
        where=where
    )
    
    # Debug Logging of Chunks and Similarity Scores
    if results and "documents" in results and results["documents"]:
        docs = results["documents"][0]
        distances = results.get("distances", [[]])[0] if "distances" in results and results["distances"] else []
        metadatas = results.get("metadatas", [[]])[0] if "metadatas" in results and results["metadatas"] else []
        
        print(f"\n=================== RAG RETRIEVAL LOG ===================")
        print(f"Collection: {collection_name} | Query: '{query}' | Target count: {n_results} | Filters: {where}")
        print(f"Retrieved {len(docs)} chunks:")
        for idx, doc in enumerate(docs):
            dist = distances[idx] if idx < len(distances) else None
            meta = metadatas[idx] if idx < len(metadatas) else {}
            # Chroma L2 distance: d=0 is identical. Convert to similarity score: 1 / (1 + d)
            est_similarity = 1.0 / (1.0 + dist) if dist is not None else 0.0
            doc_type = meta.get("doc_type", "unknown")
            print(f"  [{idx + 1}] DocType: {doc_type} | Distance: {dist:.4f} | Est Similarity: {est_similarity:.4f}")
            preview = doc.strip().replace("\n", " ")
            print(f"      Snippet: {preview[:200]}...")
        print(f"=========================================================\n")
        
        return docs
        
    return []

def delete_collection(collection_name: str):
    """
    Deletes the specified collection from ChromaDB if it exists.
    """
    chroma = get_chroma_client()
    try:
        chroma.delete_collection(collection_name)
    except Exception:
        pass
