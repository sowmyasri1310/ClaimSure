from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from services.document_service import process_and_index_pdf
from services.rag_service import hybrid_search, delete_collection
from services.groq_service import call_groq, call_groq_json

# LangGraph State Schema
class DisputeState(TypedDict):
    # Input files and metadata
    policy_pdf: bytes
    bill_pdf: bytes
    report_pdf: bytes
    user_name: str
    insurer_name: str
    user_id: str
    collection_name: str
    
    # Extracted claim data
    extracted_info: Optional[Dict[str, Any]]
    
    # Policy findings
    relevant_clauses: Optional[List[str]]
    citations: Optional[List[str]]
    
    # Mismatch analysis
    mismatch_found: Optional[bool]
    misapplied_clause: Optional[str]
    mismatch_explanation: Optional[str]
    
    # Evaluation / Scoring
    dispute_score: Optional[int]
    score_reasoning: Optional[str]
    strength: Optional[str]
    
    # Final output letter
    dispute_letter: Optional[str]

# ----------------- Nodes Implementation -----------------

def parse_documents(state: DisputeState) -> DisputeState:
    """
    Node 1: Parses policy, bill, and report PDFs, chunks them, and indexes them in ChromaDB.
    """
    collection_name = state["collection_name"]
    
    # Clear existing collection first
    delete_collection(collection_name)
    
    # Parse and index each PDF
    process_and_index_pdf(state["policy_pdf"], collection_name, "policy")
    process_and_index_pdf(state["bill_pdf"], collection_name, "bill")
    process_and_index_pdf(state["report_pdf"], collection_name, "report")
    
    return state

def extract_claim_info(state: DisputeState) -> DisputeState:
    """
    Node 2: Queries ChromaDB and calls Groq to extract treatment details, amount billed, treatment date, and rejection reason.
    """
    collection_name = state["collection_name"]
    
    # Run multiple queries on report to fetch clinical detail and service dates
    rep_q1 = hybrid_search(collection_name, "treatment procedure diagnosis patient findings medical recommendation", n_results=2, where={"doc_type": "report"})
    rep_q2 = hybrid_search(collection_name, "date of surgery date of service admission date discharge date treatment date", n_results=2, where={"doc_type": "report"})
    
    # Run multiple queries on bill to fetch billing details and rejection codes
    bill_q1 = hybrid_search(collection_name, "billed amount charge price claim status code denial rejection reason", n_results=2, where={"doc_type": "bill"})
    bill_q2 = hybrid_search(collection_name, "denial letter date of denial rejection date Clause 2.2 waiting period", n_results=2, where={"doc_type": "bill"})
    
    # Deduplicate chunks
    report_chunks = list(dict.fromkeys(rep_q1 + rep_q2))
    bill_chunks = list(dict.fromkeys(bill_q1 + bill_q2))
    
    context = "\n\n".join(report_chunks + bill_chunks)
    
    system_prompt = (
        "You are an expert medical billing auditor. Based on the hospital bill and doctor's report excerpts below, "
        "extract the main treatment performed, total amount billed, the treatment/surgery date (e.g. Oct 2024), and the rejection reason.\n"
        "Respond ONLY in this JSON format:\n"
        "{\n"
        '  "treatment_performed": "extracted treatment, procedure or service",\n'
        '  "amount_billed": "extracted billing amount or cost",\n'
        '  "treatment_date": "extracted treatment or surgery date, e.g. Oct 2024",\n'
        '  "rejection_reason": "stated reason why the insurance claim was denied or rejected"\n'
        "}\n"
        "Do not add any text outside the JSON."
    )
    
    user_message = f"Excerpts:\n{context}"
    
    extracted = call_groq_json(system_prompt, user_message, max_tokens=512)
    state["extracted_info"] = extracted
    return state

def find_policy_clauses(state: DisputeState) -> DisputeState:
    """
    Node 3: Queries ChromaDB to find the specific insurance policy clauses relating to the treatment and waiting periods.
    """
    collection_name = state["collection_name"]
    treatment = state["extracted_info"].get("treatment_performed", "medical procedure")
    rejection = state["extracted_info"].get("rejection_reason", "")
    
    # Query policy for the specific treatment coverage
    policy_treatment_chunks = hybrid_search(
        collection_name,
        query=f"{treatment} coverage exclusions co-pay deductibles limits criteria benefits",
        n_results=3,
        where={"doc_type": "policy"}
    )
    
    # Query policy for general parameters: issue date, waiting period, Clause 2.2, etc.
    policy_general_chunks = hybrid_search(
        collection_name,
        query=f"policy issue date effective date inception date waiting period Clause 2.2 exclusion period",
        n_results=3,
        where={"doc_type": "policy"}
    )
    
    # Deduplicate policy chunks
    policy_chunks = list(dict.fromkeys(policy_treatment_chunks + policy_general_chunks))
    
    context = "\n\n".join(policy_chunks)
    
    system_prompt = (
        "You are an insurance policy examiner. Analyze the policy excerpts and identify the specific clauses "
        "that apply to the medical treatment, policy issue date, waiting periods, or exclusions (like Clause 2.2) mentioned below.\n"
        "Respond ONLY in this JSON format:\n"
        "{\n"
        '  "relevant_clauses": ["exact text of clause 1", "exact text of clause 2"],\n'
        '  "analysis": "brief explanation of how these clauses relate to the treatment, policy issue date, or waiting period"\n'
        "}\n"
        "Do not add any text outside the JSON."
    )
    
    user_message = f"Treatment: {treatment}\nRejection Reason: {rejection}\n\nPolicy Excerpts:\n{context}"
    
    result = call_groq_json(system_prompt, user_message, max_tokens=1024)
    
    state["relevant_clauses"] = result.get("relevant_clauses", [])
    state["citations"] = result.get("relevant_clauses", [])
    return state

def detect_mismatches(state: DisputeState) -> DisputeState:
    """
    Node 4: Compares the doctor's report, bill, and policy clauses to detect if the rejection was valid or misapplied.
    """
    collection_name = state["collection_name"]
    info = state["extracted_info"]
    clauses = state["relevant_clauses"]
    
    clauses_text = "\n\n".join(clauses) if clauses else "No relevant policy clauses identified."
    
    # Retrieve all doctor's report and bill chunks to compare timelines, dates, and justifications
    report_chunks = hybrid_search(
        collection_name, 
        query="treatment procedure surgery diagnosis patient findings medical recommendation date of service", 
        n_results=2, 
        where={"doc_type": "report"}
    )
    bill_chunks = hybrid_search(
        collection_name, 
        query="billed amount charge price claim status code denial rejection reason service date Clause 2.2 waiting period", 
        n_results=2, 
        where={"doc_type": "bill"}
    )
    
    # Retrieve general policy chunks containing inception/issue dates and waiting period definitions
    policy_general_chunks = hybrid_search(
        collection_name,
        query="policy issue date effective date inception date waiting period Clause 2.2 exclusion period 01 Jan 2022 24 months",
        n_results=2,
        where={"doc_type": "policy"}
    )
    
    report_text = "\n\n".join(report_chunks)
    bill_text = "\n\n".join(bill_chunks)
    policy_general_text = "\n\n".join(policy_general_chunks)
    
    system_prompt = (
        "You are an expert healthcare claims dispute analyst. Your task is to perform a rigorous comparison of "
        "the relevant insurance policy clauses, the hospital bill, and the doctor's medical report to detect "
        "if the insurer's rejection was valid or if it is a wrongful denial (mismatch).\n\n"
        "Strictly adhere to the following dispute-analysis reasoning rules:\n"
        "1. Identify the Insurer's Rejection Reason: Extract the stated justification for the denial (e.g., 'waiting period not completed').\n"
        "2. Retrieve and Compare Dates & Timelines:\n"
        "   - Locate the Policy Issue/Effective Date (from the policy clauses or general excerpts, e.g. 01 Jan 2022).\n"
        "   - Locate the waiting period duration (from the policy clauses or general excerpts, e.g. 24 months).\n"
        "   - Calculate the completion date of the waiting period (Policy Issue Date + Waiting Period duration, e.g. 01 Jan 2022 + 24 months = 01 Jan 2024).\n"
        "   - Locate the actual treatment or surgery date (from the doctor's report or hospital bill, e.g. 15 Oct 2024).\n"
        "3. Evaluate Contradictions:\n"
        "   - Compare the calculated waiting period completion date with the actual surgery date.\n"
        "   - If the surgery date is AFTER the waiting period completion date, the waiting period WAS fully completed, "
        "     making the insurer's rejection ('waiting period not completed') factually incorrect and a clear policy mismatch!\n"
        "4. Classify Mismatch:\n"
        "   - If any documentary evidence contradicts the insurer's rationale (like the timelines above), classify mismatch_found as true.\n"
        "   - Explicitly cite the misapplied clause (e.g. 'Clause 2.2' or 'Waiting Period Clause') and detail the timeline contradiction in the explanation.\n\n"
        "Respond ONLY in this JSON format:\n"
        "{\n"
        '  "mismatch_found": true or false,\n'
        '  "misapplied_clause": "exact name or text of the misapplied clause, or null if none",\n'
        '  "explanation": "detailed chronological explanation of why the rejection was valid or invalid, citing specific dates (policy issue date, waiting period completion date, surgery date) and how they contradict or support the insurer\'s rejection"\n'
        "}\n"
        "Do not add any text outside the JSON."
    )
    
    user_message = (
        f"Claim Info:\n"
        f"- Treatment: {info.get('treatment_performed')}\n"
        f"- Amount: {info.get('amount_billed')}\n"
        f"- Treatment Date: {info.get('treatment_date')}\n"
        f"- Rejection Reason: {info.get('rejection_reason')}\n\n"
        f"Relevant Policy Clauses:\n{clauses_text}\n\n"
        f"General Policy Info & Inception Dates:\n{policy_general_text}\n\n"
        f"Hospital Bill Excerpts:\n{bill_text}\n\n"
        f"Doctor's Report Excerpts:\n{report_text}"
    )
    
    result = call_groq_json(system_prompt, user_message, max_tokens=1024)
    
    state["mismatch_found"] = bool(result.get("mismatch_found", False))
    state["misapplied_clause"] = result.get("misapplied_clause")
    state["mismatch_explanation"] = result.get("explanation", "")
    return state

def score_dispute(state: DisputeState) -> DisputeState:
    """
    Node 5: Scores the likelihood of winning the dispute based on mismatch findings.
    """
    system_prompt = (
        "You are an insurance dispute coordinator. Based on the mismatch analysis below, score the likelihood "
        "of winning the insurance claim dispute on a scale of 0 to 100.\n"
        "Determine:\n"
        "1. Dispute Score: integer from 0 to 100.\n"
        "   - If mismatch_found is true and there is clear evidence of a wrongful denial (e.g. waiting period completed prior to surgery), assign a high score between 80 and 95.\n"
        "   - If the denial is valid and aligned with the policy, assign a low score (0-40).\n"
        "2. Strength: 'weak' (score 0-40), 'moderate' (score 41-70), or 'strong' (score 71-100).\n"
        "3. Reasoning: 2-3 sentences explaining the rating.\n"
        "Respond ONLY in this JSON format:\n"
        "{\n"
        '  "dispute_score": 90,\n'
        '  "strength": "strong",\n'
        '  "reasoning": "explanation of score"\n'
        "}\n"
        "Do not add any text outside the JSON."
    )
    
    user_message = (
        f"Mismatch Found: {state['mismatch_found']}\n"
        f"Misapplied Clause: {state['misapplied_clause']}\n"
        f"Explanation: {state['mismatch_explanation']}"
    )
    
    result = call_groq_json(system_prompt, user_message, max_tokens=512)
    
    # Validation of fields
    score = result.get("dispute_score", 50)
    try:
        score = int(score)
    except:
        score = 50
        
    strength = result.get("strength", "moderate").lower().strip()
    if strength not in ["weak", "moderate", "strong"]:
        if score > 70:
            strength = "strong"
        elif score > 40:
            strength = "moderate"
        else:
            strength = "weak"
            
    state["dispute_score"] = score
    state["strength"] = strength
    state["score_reasoning"] = result.get("reasoning", "")
    return state

def generate_letter(state: DisputeState) -> DisputeState:
    """
    Node 6: Generates the formal appeal letter citing exact details and includes the mandatory AI disclaimer.
    """
    info = state["extracted_info"]
    clauses = state["relevant_clauses"]
    
    clauses_text = "\n".join(f"- {c}" for c in clauses) if clauses else "Referenced policy clauses"
    
    system_prompt = (
        "You are a professional healthcare advocate. Generate a formal insurance claim dispute appeal letter on behalf of the patient.\n"
        "The letter MUST:\n"
        "- Be formatted professionally, with today's date, sender address placeholder, recipient address placeholder, Subject: Appeal of Claim Denial, clear body paragraphs, and signature line.\n"
        "- Cite the exact policy clauses and findings from the doctor's report.\n"
        "- Conclude with this disclaimer at the bottom: 'This letter was generated with AI assistance and should be reviewed before submission.'\n"
        "Respond with the letter text. Do not return JSON. Just return the plain text of the letter."
    )
    
    user_message = (
        f"Patient Name: {state['user_name']}\n"
        f"Insurer Name: {state['insurer_name']}\n"
        f"Treatment Performed: {info.get('treatment_performed')}\n"
        f"Amount Billed: {info.get('amount_billed')}\n"
        f"Treatment Date: {info.get('treatment_date')}\n"
        f"Rejection Reason: {info.get('rejection_reason')}\n"
        f"Policy Clauses to cite:\n{clauses_text}\n"
        f"Dispute Score: {state['dispute_score']} (Strength: {state['strength']})\n"
        f"Mismatch Explanation: {state['mismatch_explanation']}"
    )
    
    letter_text = call_groq(system_prompt, user_message, max_tokens=2048)
    
    # Ensure disclaimer is at the end if LLM forgot it
    disclaimer = "This letter was generated with AI assistance and should be reviewed before submission."
    if disclaimer.lower() not in letter_text.lower():
        letter_text += f"\n\n---\nDisclaimer: {disclaimer}"
        
    state["dispute_letter"] = letter_text
    return state

# ----------------- Compile StateGraph -----------------

workflow = StateGraph(DisputeState)

workflow.add_node("parse_documents", parse_documents)
workflow.add_node("extract_claim_info", extract_claim_info)
workflow.add_node("find_policy_clauses", find_policy_clauses)
workflow.add_node("detect_mismatches", detect_mismatches)
workflow.add_node("score_dispute", score_dispute)
workflow.add_node("generate_letter", generate_letter)

workflow.add_edge(START, "parse_documents")
workflow.add_edge("parse_documents", "extract_claim_info")
workflow.add_edge("extract_claim_info", "find_policy_clauses")
workflow.add_edge("find_policy_clauses", "detect_mismatches")
workflow.add_edge("detect_mismatches", "score_dispute")
workflow.add_edge("score_dispute", "generate_letter")
workflow.add_edge("generate_letter", END)

dispute_agent = workflow.compile()
