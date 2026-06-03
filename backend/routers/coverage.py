from fastapi import APIRouter, File, UploadFile, Form, Depends, HTTPException
from models.schemas import CoverageResponse
from routers.auth_helper import get_current_user
from services.document_service import process_and_index_pdf
from services.rag_service import hybrid_search, delete_collection
from services.groq_service import call_groq_json

router = APIRouter()

@router.post("/check", response_model=CoverageResponse)
async def check_coverage(
    policy_pdf: UploadFile = File(...),
    query: str = Form(...),
    user_id: str = Depends(get_current_user)
):
    """
    Uploads an insurance policy PDF, indexes it in ChromaDB, and performs a RAG-based query 
    to see if a treatment is covered under that policy.
    """
    # 1. Validate file suffix
    if not policy_pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF files are allowed.")

    # 2. Read bytes and validate file size (max 10MB)
    try:
        file_bytes = await policy_pdf.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file contents: {str(e)}")
        
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")

    collection_name = f"policy_{user_id}"

    try:
        # Clear the old policy collection first to avoid mixing policies
        delete_collection(collection_name)
        
        # Index the PDF chunks
        process_and_index_pdf(file_bytes, collection_name, "policy")
        
        # Search the top-5 relevant policy clauses
        chunks = hybrid_search(collection_name, query, n_results=5, where={"doc_type": "policy"})
        
        if not chunks:
            return CoverageResponse(
                covered=False,
                confidence=0.0,
                relevant_clauses=[],
                explanation="No relevant policy clauses found in the uploaded document."
            )

        # Send policy excerpts and query to Groq
        system_prompt = (
            "You are an insurance policy analyst. Based ONLY on the policy excerpts below, "
            "answer whether the treatment is covered.\n"
            "Respond ONLY in this JSON format:\n"
            "{\n"
            '  "covered": true or false,\n'
            '  "confidence": 0.0 to 1.0,\n'
            '  "relevant_clauses": ["exact clause text from policy"],\n'
            '  "explanation": "plain language explanation"\n'
            "}\n"
            "Do not add any text outside the JSON."
        )
        
        excerpts = "\n\n".join(chunks)
        user_message = f"Policy excerpts:\n{excerpts}\n\nQuery: {query}"
        
        result = call_groq_json(system_prompt, user_message)
        
        # Ensure returned schema is valid and defaults exist
        return CoverageResponse(
            covered=bool(result.get("covered", False)),
            confidence=float(result.get("confidence", 0.0)),
            relevant_clauses=list(result.get("relevant_clauses", [])),
            explanation=str(result.get("explanation", ""))
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Coverage checking failed: {str(e)}")
