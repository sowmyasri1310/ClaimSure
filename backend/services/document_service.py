from utils.pdf_parser import extract_text_from_pdf
from utils.chunker import chunk_text
from services.rag_service import embed_chunks

def process_and_index_pdf(file_bytes: bytes, collection_name: str, doc_type: str) -> list[str]:
    """
    Parses a PDF, chunks its text, and stores the chunks in the user's ChromaDB collection.
    `doc_type` metadata should be "policy" | "bill" | "report".
    Returns the generated list of text chunks.
    """
    # 1. Extract text from PDF
    text = extract_text_from_pdf(file_bytes)
    
    # 2. Chunk text (500 tokens/words, 50 overlap)
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    
    # 3. Create metadata list
    metadata_list = [{"doc_type": doc_type} for _ in range(len(chunks))]
    
    # 4. Embed chunks and save in ChromaDB
    embed_chunks(chunks, collection_name, metadata_list)
    
    return chunks
