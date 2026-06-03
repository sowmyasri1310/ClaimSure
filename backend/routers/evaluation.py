from fastapi import APIRouter, HTTPException
from models.schemas import EvaluationRequest, EvaluationResponse
from services.evaluation_service import run_evaluation

router = APIRouter()

@router.post("", response_model=EvaluationResponse)
async def evaluate_rag(request: EvaluationRequest):
    """
    Evaluates RAG generation faithfulness and answer relevancy.
    """
    try:
        scores = run_evaluation(
            question=request.question,
            answer=request.answer,
            contexts=request.contexts
        )
        return EvaluationResponse(
            faithfulness=scores.get("faithfulness", 0.0),
            answer_relevancy=scores.get("answer_relevancy", 0.0)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Evaluation failed: {str(e)}"
        )
