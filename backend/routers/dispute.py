from fastapi import APIRouter, File, UploadFile, Form, Depends, HTTPException
from models.schemas import DisputeResponse
from routers.auth_helper import get_current_user
from services.dispute_agent import dispute_agent
from models.database import save_dispute_case

router = APIRouter()

@router.post("/analyze", response_model=DisputeResponse)
async def analyze_dispute(
    policy_pdf: UploadFile = File(...),
    bill_pdf: UploadFile = File(...),
    report_pdf: UploadFile = File(...),
    user_name: str = Form(...),
    insurer_name: str = Form(...),
    user_id: str = Depends(get_current_user)
):
    """
    Receives policy, bill, and report PDFs, runs them through the LangGraph dispute resolver,
    saves the final result to MongoDB, and returns the case analysis.
    """
    # 1. Suffix checking
    for file_name, upload_file in [("policy_pdf", policy_pdf), ("bill_pdf", bill_pdf), ("report_pdf", report_pdf)]:
        if not upload_file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid format for {file_name}. Only PDF documents are allowed."
            )

    # 2. Read bytes and size checking
    try:
        policy_bytes = await policy_pdf.read()
        bill_bytes = await bill_pdf.read()
        report_bytes = await report_pdf.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read upload contents: {str(e)}")

    for file_name, file_bytes in [("policy_pdf", policy_bytes), ("bill_pdf", bill_bytes), ("report_pdf", report_bytes)]:
        if len(file_bytes) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=400, 
                detail=f"File {file_name} exceeds the 10MB size limit."
            )

    collection_name = f"dispute_{user_id}"

    try:
        # Prepare LangGraph state
        inputs = {
            "policy_pdf": policy_bytes,
            "bill_pdf": bill_bytes,
            "report_pdf": report_bytes,
            "user_name": user_name,
            "insurer_name": insurer_name,
            "user_id": user_id,
            "collection_name": collection_name,
            "extracted_info": None,
            "relevant_clauses": None,
            "citations": None,
            "mismatch_found": None,
            "misapplied_clause": None,
            "mismatch_explanation": None,
            "dispute_score": None,
            "score_reasoning": None,
            "strength": None,
            "dispute_letter": None,
            "confidence_score": None,
            "faithfulness_score": None,
            "hallucination_risk": None
        }

        # Invoke the LangGraph workflow
        result_state = dispute_agent.invoke(inputs)

        # Build response schema mapping
        response_data = {
            "mismatch_found": bool(result_state.get("mismatch_found", False)),
            "misapplied_clause": result_state.get("misapplied_clause"),
            "dispute_score": int(result_state.get("dispute_score", 0)),
            "score_reasoning": str(result_state.get("score_reasoning", "")),
            "strength": result_state.get("strength", "moderate"),
            "dispute_letter": str(result_state.get("dispute_letter", "")),
            "citations": list(result_state.get("citations", [])),
            "confidence_score": int(result_state.get("confidence_score", 0)),
            "faithfulness_score": int(result_state.get("faithfulness_score", 0)),
            "hallucination_risk": int(result_state.get("hallucination_risk", 0))
        }

        # Persist case to MongoDB async
        await save_dispute_case(user_id, insurer_name, response_data)

        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"An error occurred during claims dispute analysis: {str(e)}"
        )
