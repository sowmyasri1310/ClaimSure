from pydantic import BaseModel, Field
from typing import List, Literal, Optional

# Triage Schemas
class TriageRequest(BaseModel):
    symptoms: str = Field(..., description="Symptoms experienced by the user")
    age: int = Field(..., description="Age of the user")
    existing_conditions: str = Field(..., description="Existing health conditions/comorbidities")

class TriageResponse(BaseModel):
    specialist: str
    urgency: Literal["low", "medium", "high"]
    reasoning: str
    pre_visit_checklist: List[str]

# Coverage Check Schemas
class CoverageResponse(BaseModel):
    covered: bool
    confidence: float
    relevant_clauses: List[str]
    explanation: str

# Dispute Schemas
class DisputeResponse(BaseModel):
    mismatch_found: bool
    misapplied_clause: Optional[str] = None
    dispute_score: int
    score_reasoning: str
    strength: Literal["weak", "moderate", "strong"]
    dispute_letter: str
    citations: List[str]
    confidence_score: int
    faithfulness_score: int
    hallucination_risk: int

# Evaluation Schemas
class EvaluationRequest(BaseModel):
    question: str
    answer: str
    contexts: List[str]

class EvaluationResponse(BaseModel):
    faithfulness: float
    answer_relevancy: float
