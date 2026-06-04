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
    
    # Debug / verification info (optional/extra)
    policy_start_date: Optional[str]
    waiting_period: Optional[str]
    waiting_period_completion_date: Optional[str]
    surgery_date: Optional[str]
    coverage_status: Optional[str]


# ----------------- Nodes Implementation -----------------

def trace_node(node_name: str, stage: str, state: DisputeState):
    """
    Prints incoming/outgoing state trace for LangGraph nodes.
    stage: 'incoming' or 'outgoing'
    """
    # Clean state for printing
    clean_state = {}
    for k, v in state.items():
        if k in ("policy_pdf", "bill_pdf", "report_pdf"):
            clean_state[k] = f"<{len(v)} bytes>" if v else "None"
        else:
            clean_state[k] = v
            
    print(f"\n==================== NODE: {node_name} ({stage.upper()}) ====================")
    print(f"State dict: {clean_state}")
    print(f"dispute_score: {state.get('dispute_score')}")
    print(f"mismatch_found: {state.get('mismatch_found')}")
    print(f"strength: {state.get('strength')}")
    print("=================================================================\n")


def parse_documents(state: DisputeState) -> DisputeState:
    """
    Node 1: Parses policy, bill, and report PDFs, chunks them, and indexes them in ChromaDB.
    """
    node_name = "parse_documents"
    incoming_score = state.get("dispute_score")
    trace_node(node_name, "incoming", state)
    
    collection_name = state["collection_name"]
    
    # Clear existing collection first
    delete_collection(collection_name)
    
    # Parse and index each PDF
    process_and_index_pdf(state["policy_pdf"], collection_name, "policy")
    process_and_index_pdf(state["bill_pdf"], collection_name, "bill")
    process_and_index_pdf(state["report_pdf"], collection_name, "report")
    
    trace_node(node_name, "outgoing", state)
    print(f"\n{node_name.upper()}")
    print(f"Incoming score: {incoming_score}")
    print(f"Outgoing score: {state.get('dispute_score')}\n")
    return state


def extract_claim_info(state: DisputeState) -> DisputeState:
    """
    Node 2: Queries ChromaDB and calls Groq to extract treatment details, amount billed, treatment date, and rejection reason.
    """
    node_name = "extract_claim_info"
    incoming_score = state.get("dispute_score")
    trace_node(node_name, "incoming", state)
    
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
    
    trace_node(node_name, "outgoing", state)
    print(f"\n{node_name.upper()}")
    print(f"Incoming score: {incoming_score}")
    print(f"Outgoing score: {state.get('dispute_score')}\n")
    return state


def find_policy_clauses(state: DisputeState) -> DisputeState:
    """
    Node 3: Queries ChromaDB to find the specific insurance policy clauses relating to the treatment and waiting periods.
    """
    node_name = "find_policy_clauses"
    incoming_score = state.get("dispute_score")
    trace_node(node_name, "incoming", state)
    
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
    
    trace_node(node_name, "outgoing", state)
    print(f"\n{node_name.upper()}")
    print(f"Incoming score: {incoming_score}")
    print(f"Outgoing score: {state.get('dispute_score')}\n")
    return state


def detect_mismatches(state: DisputeState) -> DisputeState:
    """
    Node 4: Compares the doctor's report, bill, and policy clauses to detect if the rejection was valid or misapplied.
    """
    import re
    import math
    from datetime import datetime
    
    node_name = "detect_mismatches"
    incoming_score = state.get("dispute_score")
    trace_node(node_name, "incoming", state)
    
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
    
    def parse_date(date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        date_str = date_str.strip()
        
        formats = [
            "%d %b %Y",      # 01 Jan 2025
            "%d %B %Y",      # 01 January 2025
            "%d-%b-%Y",      # 01-Jan-2025
            "%d-%B-%Y",      # 01-January-2025
            "%d/%m/%Y",      # 01/01/2025
            "%d-%m-%Y",      # 01-01-2025
            "%Y-%m-%d",      # 2025-01-01
            "%Y/%m/%d",      # 2025/01/01
            "%m/%d/%Y",      # 01/01/2025
            "%B %d, %Y",     # January 1, 2025
            "%b %d, %Y",     # Jan 1, 2025
            "%b %Y",         # Oct 2024
            "%B %Y"          # October 2024
        ]
        
        clean_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
        clean_str = clean_str.replace(".", "")
        clean_str = re.sub(r'\s+', ' ', clean_str)
        clean_str = re.sub(r'^[^\w]+|[^\w]+$', '', clean_str)
        
        for fmt in formats:
            try:
                return datetime.strptime(clean_str, fmt)
            except ValueError:
                continue
                
        months_map = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
            'january': 1, 'february': 2, 'march': 3, 'april': 4, 'june': 6,
            'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        # Match DD-Month-YYYY or DD Month YYYY or DD/Month/YYYY
        match = re.search(r'(\d{1,2})[\s\-_/]+([a-zA-Z]+)[\s\-_/]+(\d{4})', clean_str)
        if match:
            day = int(match.group(1))
            month_name = match.group(2).lower()
            year = int(match.group(3))
            month = months_map.get(month_name)
            if month:
                try:
                    return datetime(year, month, day)
                except ValueError:
                    pass
                    
        match = re.search(r'([a-zA-Z]+)[\s\-_/]+(\d{1,2})[\s\-_/,]+(\d{4})', clean_str)
        if match:
            month_name = match.group(1).lower()
            day = int(match.group(2))
            year = int(match.group(3))
            month = months_map.get(month_name)
            if month:
                try:
                    return datetime(year, month, day)
                except ValueError:
                    pass
                    
        match = re.search(r'([a-zA-Z]+)[\s\-_/]+(\d{4})', clean_str)
        if match:
            month_name = match.group(1).lower()
            year = int(match.group(2))
            month = months_map.get(month_name)
            if month:
                return datetime(year, month, 1)
                
        match = re.search(r'(\d{1,2})/(\d{4})', clean_str)
        if match:
            month = int(match.group(1))
            year = int(match.group(2))
            try:
                return datetime(year, month, 1)
            except ValueError:
                pass
                
        # Match YYYY/MM/DD
        match = re.search(r'(\d{4})[\s\-_/]+(\d{1,2})[\s\-_/]+(\d{1,2})', clean_str)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            try:
                return datetime(year, month, day)
            except ValueError:
                pass
                
        # Match DD/MM/YYYY or MM/DD/YYYY
        match = re.search(r'(\d{1,2})[\s\-_/]+(\d{1,2})[\s\-_/]+(\d{4})', clean_str)
        if match:
            val1 = int(match.group(1))
            val2 = int(match.group(2))
            year = int(match.group(3))
            if val2 <= 12:
                day = val1
                month = val2
            else:
                day = val2
                month = val1
            try:
                return datetime(year, month, day)
            except ValueError:
                pass

        match = re.search(r'\b(\d{4})\b', clean_str)
        if match:
            year = int(match.group(1))
            return datetime(year, 1, 1)
            
        return None

    def parse_waiting_period_months(wp_str: str) -> int:
        if not wp_str:
            return 0
        match = re.search(r'(\d+)\s*(month|year)', wp_str.lower())
        if match:
            val = int(match.group(1))
            unit = match.group(2)
            if 'year' in unit:
                return val * 12
            return val
        match = re.search(r'(\d+)', wp_str)
        if match:
            return int(match.group(1))
        return 0

    def add_months_to_date(start_date: datetime, months: int) -> datetime:
        import calendar
        month = start_date.month - 1 + months
        year = start_date.year + month // 12
        month = month % 12 + 1
        day = min(start_date.day, calendar.monthrange(year, month)[1])
        return datetime(year, month, day)

    def get_case_insensitive(d, key, default=None):
        if not d:
            return default
        for k, v in d.items():
            if k.lower() == key.lower():
                return v
        return default

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

    # Extract exact facts using Groq (preventing hallucinated calculations)
    extract_prompt = (
        "You are an insurance claim data extractor. Your task is to extract exact dates and facts "
        "from the provided documents. Do not calculate anything, do not assume, and do not invent any dates. "
        "If a value is not explicitly stated, return null.\n\n"
        "In particular, distinguish between the current policy/renewal period start date and the original inception/first issued date of the policy:\n"
        "- policy_period_start_date: The start date of the current policy period or renewal period (e.g. '01 Jan 2024').\n"
        "- original_inception_date: The date when the policy was first issued or originally became effective (e.g. '01 Jan 2022'). Look for phrases like 'first issued on', 'original inception date', 'originally active since', etc.\n\n"
        "Respond ONLY in this JSON format:\n"
        "{\n"
        '  "policy_period_start_date": "Current policy period/renewal start date or null",\n'
        '  "original_inception_date": "Original policy inception/first issued date or null",\n'
        '  "waiting_period": "Waiting period duration (e.g. 24 months, 2 years) or null",\n'
        '  "waiting_period_clause": "Clause identifier for the waiting period (e.g. Clause 2.2) or null",\n'
        '  "surgery_date": "Surgery or treatment date (e.g. 10 Aug 2025) or null",\n'
        '  "treatment_covered": "yes/no/unspecified (is this treatment covered under the policy?)",\n'
        '  "rejection_reason": "Reason for denial from the bill or denial letter or null"\n'
        "}\n"
        "Do not include any other text."
    )
    
    extracted_facts = call_groq_json(extract_prompt, user_message, max_tokens=512)
    
    policy_period_start_str = get_case_insensitive(extracted_facts, "policy_period_start_date")
    original_inception_str = get_case_insensitive(extracted_facts, "original_inception_date")
    
    if original_inception_str:
        policy_start_str = original_inception_str
    else:
        policy_start_str = policy_period_start_str
        
    print("Policy Period Date:", policy_period_start_str)
    print("Original Inception Date:", original_inception_str)
    print("Chosen Policy Start Date:", policy_start_str)
    
    waiting_period_str = get_case_insensitive(extracted_facts, "waiting_period")
    surgery_date_str = get_case_insensitive(extracted_facts, "surgery_date")
    treatment_covered_str = get_case_insensitive(extracted_facts, "treatment_covered")
    rejection_reason_str = get_case_insensitive(extracted_facts, "rejection_reason")
    wp_clause = get_case_insensitive(extracted_facts, "waiting_period_clause")
    policy_start = parse_date(policy_start_str)
    wp_months = parse_waiting_period_months(waiting_period_str)
    surgery_dt = parse_date(surgery_date_str)
    
    print(f"DEBUG: policy_start_str={policy_start_str} -> parsed={policy_start}")
    print(f"DEBUG: waiting_period_str={waiting_period_str} -> parsed_months={wp_months}")
    print(f"DEBUG: surgery_date_str={surgery_date_str} -> parsed={surgery_dt}")
    
    # Calculate waiting period completion date
    wp_completion = None
    if policy_start and wp_months > 0:
        wp_completion = add_months_to_date(policy_start, wp_months)
        print(f"DEBUG: Calculated wp_completion={wp_completion}")
        
    waiting_period_violation = False
    if surgery_dt and wp_completion:
        if surgery_dt < wp_completion:
            waiting_period_violation = True
            
    print(f"DEBUG: waiting_period_violation={waiting_period_violation}")
    print("================================================")
    print("RAW EXTRACTED FACTS")
    print(extracted_facts)
    print("================================================")
            
    mismatch_found = False
    misapplied_clause = None
    explanation = ""
    
    if waiting_period_violation:
        mismatch_found = False
        misapplied_clause = None
        explanation = (
            f"The policy started on {policy_start_str} with a waiting period of {waiting_period_str}. "
            f"The waiting period was completed on {wp_completion.strftime('%d %b %Y') if wp_completion else 'N/A'}. "
            f"The surgery occurred on {surgery_date_str}, which is before the waiting period was completed. "
            f"Therefore, the insurer's rejection is valid according to the policy terms."
        )
    elif policy_start and wp_months > 0 and surgery_dt and wp_completion and surgery_dt >= wp_completion:
        # Check if rejection reason is waiting-period related
        is_wp_rejection = False
        if rejection_reason_str:
            rejection_lower = rejection_reason_str.lower()
            if "waiting" in rejection_lower or "2.2" in rejection_lower or "inception" in rejection_lower or "period" in rejection_lower:
                is_wp_rejection = True
                
        if is_wp_rejection:
            mismatch_found = True
            misapplied_clause = wp_clause if wp_clause else "Waiting Period Clause"
            explanation = (
                f"The policy started on {policy_start_str} with a waiting period of {waiting_period_str}. "
                f"The waiting period was completed on {wp_completion.strftime('%d %b %Y')}. "
                f"The surgery occurred on {surgery_date_str}, which is after the waiting period completion date. "
                f"Therefore, the insurer's rejection based on the waiting period is invalid and contradicts the policy terms."
            )
        else:
            # Check other reasons via LLM
            eval_prompt = (
                "You are an expert claims dispute auditor. Analyze the following extracted documents and facts. "
                "Determine if there is a genuine contradiction (mismatch) between the policy terms and the insurer's rejection.\n"
                "Guidelines:\n"
                "1. If the policy, doctor report, and hospital bill all support the rejection, set mismatch_found to false.\n"
                "2. If the policy supports the claim (e.g. the service is explicitly covered) and the rejection directly contradicts it, set mismatch_found to true.\n"
                "3. Do not invent any facts or dates.\n\n"
                "Respond ONLY in this JSON format:\n"
                "{\n"
                '  "mismatch_found": true or false,\n'
                '  "misapplied_clause": "exact name or text of the misapplied clause, or null if none",\n'
                '  "explanation": "detailed chronological explanation of the decision, referencing specific facts and dates"\n'
                "}\n"
                "Do not include any other text."
            )
            eval_res = call_groq_json(eval_prompt, user_message, max_tokens=512)
            mismatch_found = bool(get_case_insensitive(eval_res, "mismatch_found", False))
            misapplied_clause = get_case_insensitive(eval_res, "misapplied_clause")
            explanation = get_case_insensitive(eval_res, "explanation", "")
    else:
        # General case (e.g. missing dates) - evaluate via LLM
        eval_prompt = (
            "You are an expert claims dispute auditor. Analyze the following extracted documents and facts. "
            "Determine if there is a genuine contradiction (mismatch) between the policy terms and the insurer's rejection.\n"
            "Guidelines:\n"
            "1. If the policy, doctor report, and hospital bill all support the rejection, set mismatch_found to false.\n"
            "2. If the policy supports the claim (e.g. the service is explicitly covered) and the rejection directly contradicts it, set mismatch_found to true.\n"
            "3. Do not invent any facts or dates.\n\n"
            "Respond ONLY in this JSON format:\n"
            "{\n"
                '  "mismatch_found": true or false,\n'
                '  "misapplied_clause": "exact name or text of the misapplied clause, or null if none",\n'
                '  "explanation": "detailed chronological explanation of the decision, referencing specific facts and dates"\n'
            "}\n"
            "Do not include any other text."
        )
        eval_res = call_groq_json(eval_prompt, user_message, max_tokens=512)
        mismatch_found = bool(get_case_insensitive(eval_res, "mismatch_found", False))
        misapplied_clause = get_case_insensitive(eval_res, "misapplied_clause")
        explanation = get_case_insensitive(eval_res, "explanation", "")

    state["mismatch_found"] = mismatch_found
    state["misapplied_clause"] = misapplied_clause
    state["mismatch_explanation"] = explanation
    
    # Store for debug logging
    state["policy_start_date"] = policy_start_str
    state["waiting_period"] = waiting_period_str
    state["waiting_period_completion_date"] = wp_completion.strftime('%d %b %Y') if wp_completion else "N/A"
    state["surgery_date"] = surgery_date_str
    state["coverage_status"] = treatment_covered_str
    
    trace_node(node_name, "outgoing", state)
    print(f"\n{node_name.upper()}")
    print(f"Incoming score: {incoming_score}")
    print(f"Outgoing score: {state.get('dispute_score')}\n")
    print("\n===== FINAL MISMATCH DECISION =====")
    print("policy_start =", policy_start_str)
    print("waiting_period =", waiting_period_str)
    print("surgery_date =", surgery_date_str)
    print("wp_completion =", wp_completion)
    print("waiting_period_violation =", waiting_period_violation)
    print("FINAL mismatch_found =", mismatch_found)
    print("FINAL explanation =", explanation)
    print("===================================\n")
    
    return state


def score_dispute(state: DisputeState) -> DisputeState:
    """
    Node 5: Scores the likelihood of winning the dispute based on mismatch findings and evidence quality.
    """
    node_name = "score_dispute"
    incoming_score = state.get("dispute_score")
    trace_node(node_name, "incoming", state)
    
    mismatch_found = state.get("mismatch_found", False)
    
    system_prompt = (
        "You are an expert insurance dispute coordinator. Your job is to assign an evidence-driven dispute score (0 to 100) "
        "representing the likelihood that a dispute/appeal would succeed, calculated from the actual evidence in all three uploaded documents.\n\n"
        "You MUST calculate the score using the following category points (summing up to the Final Score, bounded between 0 and 100):\n"
        "1. Policy Coverage Support (up to +30 or down to -30 points: does policy support claim or exclude it?)\n"
        "2. Rejection Validity / Ambiguity (up to +20 or down to -20 points: is rejection invalid/unsupported/ambiguous?)\n"
        "3. Waiting Period Compliance (up to +15 or down to 0 points: waiting period satisfied or violated?)\n"
        "4. Coverage Strength / Exclusions (up to +15 or down to -15 points: explicitly covered, partially, or excluded?)\n"
        "5. Medical Necessity (Doctor Report) (up to +10 or down to 0 points: strong doctor justification?)\n"
        "6. Documentation Quality (up to +10 or down to -10 points: complete vs missing/contradictory evidence?)\n"
        "7. Clause Contradiction Severity (up to +10 or down to 0 points: direct clause contradiction/misapplication?)\n\n"
        "Your score and strength MUST align with these real-world scenarios:\n"
        "- Case 1 (Policy clearly supports insurer, waiting period not completed, valid denial): score 0 to 20, strength: 'weak'\n"
        "- Case 2 (Policy mostly supports insurer but has ambiguity/loopholes): score 20 to 45, strength: 'weak' or 'moderate'\n"
        "- Case 3 (Evidence is mixed/conflicting): score 45 to 65, strength: 'moderate'\n"
        "- Case 4 (Policy mostly covers treatment, patient has strong grounds): score 65 to 85, strength: 'strong'\n"
        "- Case 5 (Policy clearly covers treatment, waiting period is satisfied, insurer directly contradicts policy): score 85 to 100, strength: 'strong'\n\n"
        "You MUST respond ONLY with a JSON object in this format:\n"
        "{\n"
        '  "dispute_score": <calculated_score_integer>,\n'
        '  "strength": "weak" | "moderate" | "strong",\n'
        '  "reasoning": "Policy Coverage Support: <+30 to -30>\\nRejection Validity / Ambiguity: <+20 to -20>\\nWaiting Period Compliance: <+15 to 0>\\nCoverage Strength / Exclusions: <+15 to -15>\\nMedical Necessity (Doctor Report): <+10 to 0>\\nDocumentation Quality: <+10 to -10>\\nClause Contradiction Severity: <+10 to 0>\\n\\nFinal Score: <calculated_score>\\n\\nFinal Reasoning: <detailed explanation of why points were added/deducted based on evidence>"\n'
        "}\n"
        "Do not include any other text outside the JSON."
    )
        
    user_message = (
        f"FACTS EXTRACTED FROM DOCUMENTS:\n"
        f"- Mismatch Found: {mismatch_found}\n"
        f"- Misapplied Clause: {state.get('misapplied_clause')}\n"
        f"- Mismatch Explanation: {state.get('mismatch_explanation')}\n"
        f"- Policy Start Date: {state.get('policy_start_date')}\n"
        f"- Waiting Period: {state.get('waiting_period')}\n"
        f"- Waiting Period Completion Date: {state.get('waiting_period_completion_date')}\n"
        f"- Surgery Date: {state.get('surgery_date')}\n"
        f"- Coverage Status: {state.get('coverage_status')}\n"
        f"- Extracted Claim Info: {state.get('extracted_info')}\n"
        f"- Relevant Policy Clauses: {state.get('relevant_clauses')}\n"
    )
    
    result = call_groq_json(system_prompt, user_message, max_tokens=512)
    
    # Validation of fields
    score = result.get("dispute_score", 50)
    try:
        score = int(score)
    except:
        score = 50
        
    score = min(max(score, 0), 100)
    
    strength = result.get("strength", "moderate").lower().strip()
    if strength not in ("weak", "moderate", "strong"):
        if score <= 20:
            strength = "weak"
        elif score <= 45:
            strength = "weak"  # Or moderate
        elif score <= 65:
            strength = "moderate"
        else:
            strength = "strong"
        
    state["dispute_score"] = score
    state["strength"] = strength
    state["score_reasoning"] = result.get("reasoning", "")
    
    # Debug logging in backend logs
    print("================== DISPUTE REASONING AUDIT LOG ==================")
    print(f"Policy Start Date: {state.get('policy_start_date')}")
    print(f"Waiting Period: {state.get('waiting_period')}")
    print(f"Waiting Period Completion Date: {state.get('waiting_period_completion_date')}")
    print(f"Surgery Date: {state.get('surgery_date')}")
    print(f"Coverage Status: {state.get('coverage_status')}")
    print(f"Mismatch Found: {mismatch_found}")
    print(f"Final Dispute Score: {score}")
    print(f"Strength Case: {strength}")
    print("=================================================================")
    
    trace_node(node_name, "outgoing", state)
    print(f"\n{node_name.upper()}")
    print(f"Incoming score: {incoming_score}")
    print(f"Outgoing score: {state.get('dispute_score')}\n")
    return state


def generate_letter(state: DisputeState) -> DisputeState:
    """
    Node 6: Generates the formal appeal letter citing exact details and includes the mandatory AI disclaimer.
    """
    node_name = "generate_letter"
    incoming_score = state.get("dispute_score")
    trace_node(node_name, "incoming", state)
    
    if not state.get("mismatch_found", False):
        state["dispute_letter"] = "Based on the submitted documents, the insurer's decision appears consistent with the policy terms. An appeal is unlikely to succeed."
        trace_node(node_name, "outgoing", state)
        print(f"\n{node_name.upper()}")
        print(f"Incoming score: {incoming_score}")
        print(f"Outgoing score: {state.get('dispute_score')}\n")
        return state
        
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
    
    trace_node(node_name, "outgoing", state)
    print(f"\n{node_name.upper()}")
    print(f"Incoming score: {incoming_score}")
    print(f"Outgoing score: {state.get('dispute_score')}\n")
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
