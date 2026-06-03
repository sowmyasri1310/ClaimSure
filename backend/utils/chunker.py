def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Splits text into chunks of specified word length with overlap.
    """
    words = text.split()
    chunks = []
    
    # Avoid infinite loop if overlap >= chunk_size
    if overlap >= chunk_size:
        overlap = chunk_size // 2
        
    step = chunk_size - overlap
    if step <= 0:
        step = 1

    for i in range(0, len(words), step):
        chunk_words = words[i:i + chunk_size]
        chunk = " ".join(chunk_words)
        if chunk.strip():
            chunks.append(chunk)
            
    return chunks
