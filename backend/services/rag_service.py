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

def get_embeddings_api(texts: list[str]) -> list[list[float]]:
    """
    Tries to generate embeddings using the Hugging Face Inference API.
    Returns None if the API request fails or is rate-limited.
    """
    import urllib.request
    import json
    
    model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    if "/" not in model_name:
        url = f"https://api-inference.huggingface.co/models/sentence-transformers/{model_name}"
    else:
        url = f"https://api-inference.huggingface.co/models/{model_name}"
        
    data = {"inputs": texts}
    headers = {"Content-Type": "application/json"}
    
    # Check if a HF token is configured in the environment
    hf_token = os.getenv("HF_TOKEN")
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"
        
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
    
    try:
        # Set a short timeout (e.g., 5 seconds) to avoid hanging
        with urllib.request.urlopen(req, timeout=5) as response:
            res = json.loads(response.read().decode("utf-8"))
            if isinstance(res, list) and len(res) == len(texts):
                return res
            if isinstance(res, dict) and "error" in res:
                print(f"HF Inference API returned an error: {res['error']}")
    except Exception as e:
        print(f"HF Inference API request failed: {str(e)}")
        
    return None

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

def check_embedding_fallback(operation_name: str):
    """
    Checks if local SentenceTransformer fallback is disabled to prevent OOM crash.
    """
    if os.getenv("RENDER") or os.getenv("DISABLE_LOCAL_EMBEDDING", "false").lower() == "true":
        raise RuntimeError(
            f"Hugging Face Inference API request failed during {operation_name} (possibly due to rate limits or invalid/missing HF_TOKEN). "
            "Local SentenceTransformer fallback is disabled on Render/constrained environments to prevent Out-Of-Memory (OOM) crashes. "
            "Please configure a valid 'HF_TOKEN' environment variable in your Render service settings."
        )

def embed_chunks(chunks: list[str], collection_name: str, metadata_list: list[dict]):
    """
    Embeds raw text chunks and uploads them to a specific ChromaDB collection.
    """
    if not chunks:
        return
        
    chroma = get_chroma_client()
    
    # Try Hugging Face Inference API first to save memory (especially on Render Free Tier)
    embeddings = get_embeddings_api(chunks)
    
    if embeddings is None:
        check_embedding_fallback("document chunk embedding")
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
    embeddings = get_embeddings_api([query])
    
    if embeddings is None:
        check_embedding_fallback("query embedding search")
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
