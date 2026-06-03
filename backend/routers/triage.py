from fastapi import APIRouter, HTTPException
from models.schemas import TriageRequest, TriageResponse
from services.groq_service import call_groq_json
import re

router = APIRouter()

# Pattern for simple greetings
GREETINGS_PATTERN = re.compile(
    r"^(hi|hello|hey|yo|hola|howdy|greetings|good morning|good afternoon|good evening)( assistant| there| claimsure)?\s*[?.!]*$",
    re.IGNORECASE
)

@router.post("/analyze", response_model=TriageResponse)
async def analyze_triage(request: TriageRequest):
    """
    Analyzes user symptoms, age, and existing conditions, and recommends a medical specialist and urgency level.
    """
    # Check for simple greetings and bypass model
    if GREETINGS_PATTERN.match(request.symptoms.strip()):
        return {
            "specialist": "N/A",
            "urgency": "low",
            "reasoning": "I'm here only to provide medical assistance. Please describe your symptoms or medical concern.",
            "pre_visit_checklist": []
        }

    system_prompt = (
        "You are a medical triage assistant. Based on the symptoms, age, and existing conditions provided, "
        "respond ONLY in this JSON format:\n"
        "{\n"
        '  "specialist": "type of doctor to see",\n'
        '  "urgency": "low or medium or high",\n'
        '  "reasoning": "plain language explanation in 2-3 sentences",\n'
        '  "pre_visit_checklist": ["item1", "item2", "item3"]\n'
        "}\n"
        "Do not add any text outside the JSON."
    )
    
    user_message = (
        f"Age: {request.age}\n"
        f"Symptoms: {request.symptoms}\n"
        f"Existing Conditions: {request.existing_conditions}"
    )
    
    try:
        result = call_groq_json(system_prompt, user_message)
        # Ensure values align with expected types
        if "urgency" in result:
            result["urgency"] = result["urgency"].lower().strip()
            if result["urgency"] not in ["low", "medium", "high"]:
                result["urgency"] = "medium"  # fallback default
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Triage analysis failed: {str(e)}")
