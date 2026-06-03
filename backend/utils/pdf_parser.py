import fitz  # PyMuPDF

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extracts all text from a PDF document passed as bytes.
    """
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        return "\n".join(page.get_text() for page in doc)
    except Exception as e:
        raise ValueError(f"Error parsing PDF document: {str(e)}")
