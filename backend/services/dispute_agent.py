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

    # Structured facts preserved from early stages
    original_inception_date: Optional[str]
    policy_period_start_date: Optional[str]
    waiting_period_clause_text: Optional[str]
    coverage_clauses_text: Optional[List[str]]
    exclusion_clauses_text: Optional[List[str]]
    emergency_exceptions_text: Optional[str]
    medical_necessity_findings_text: Optional[str]

    # Structured facts dictionary containing preserved evidence
    structured_facts: Optional[Dict[str, Any]]
    retrieved_policy_chunks: Optional[List[str]]


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
    
    # Run multiple queries on report to fetch clinical detail and service dates (robustness: n_results=3)
    rep_q1 = hybrid_search(collection_name, "treatment procedure diagnosis patient findings medical recommendation", n_results=3, where={"doc_type": "report"})
    rep_q2 = hybrid_search(collection_name, "date of surgery date of service admission date discharge date treatment date", n_results=3, where={"doc_type": "report"})
    
    # Run multiple queries on bill to fetch billing details and rejection codes (robustness: n_results=3)
    bill_q1 = hybrid_search(collection_name, "billed amount charge price claim status code denial rejection reason", n_results=3, where={"doc_type": "bill"})
    bill_q2 = hybrid_search(collection_name, "denial letter date of denial rejection date Clause 2.2 waiting period", n_results=3, where={"doc_type": "bill"})
    
    # Deduplicate chunks
    report_chunks = list(dict.fromkeys(rep_q1 + rep_q2))
    bill_chunks = list(dict.fromkeys(bill_q1 + bill_q2))
    
    # Debug logging for retrieved chunks
    print(f"\n===== RETRIEVED REPORT & BILL CHUNKS FOR {node_name.upper()} =====")
    for idx, chunk in enumerate(report_chunks + bill_chunks):
        print(f"Chunk {idx+1}:\n{chunk[:300]}...\n")
    print("==============================================================\n")
    
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
    
    # 1. Coverage query
    coverage_query = f"{treatment} coverage benefits inclusion policy rules"
    coverage_chunks = hybrid_search(collection_name, query=coverage_query, n_results=4, where={"doc_type": "policy"})
    
    # 2. Exclusion query
    exclusion_query = f"{treatment} exclusions not covered limitation exceptions Clause 2.2"
    exclusion_chunks = hybrid_search(collection_name, query=exclusion_query, n_results=4, where={"doc_type": "policy"})
    
    # 3. Waiting period query
    waiting_period_query = "waiting period exclusion period inception date Clause 2.2 first issued"
    waiting_period_chunks = hybrid_search(collection_name, query=waiting_period_query, n_results=4, where={"doc_type": "policy"})
    
    # 4. Exception / emergency query
    exception_query = "emergency exception medical necessity exception urgent care exception clauses"
    exception_chunks = hybrid_search(collection_name, query=exception_query, n_results=4, where={"doc_type": "policy"})
    
    # Deduplicate policy chunks
    policy_chunks = list(dict.fromkeys(coverage_chunks + exclusion_chunks + waiting_period_chunks + exception_chunks))
    
    # Save the raw chunks in the state to ensure later stages never rely on a single retrieved chunk
    state["retrieved_policy_chunks"] = policy_chunks
    
    # Debug logging for retrieved policy chunks
    print(f"\n===== RETRIEVED POLICY CHUNKS FOR {node_name.upper()} =====")
    for idx, chunk in enumerate(policy_chunks):
        print(f"Chunk {idx+1}:\n{chunk[:300]}...\n")
    print("===========================================================\n")
    
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
    
    # Retrieve doctor's report and bill chunks (robustness: n_results=3)
    report_chunks = hybrid_search(
        collection_name, 
        query="treatment procedure surgery diagnosis patient findings medical recommendation date of service", 
        n_results=3, 
        where={"doc_type": "report"}
    )
    bill_chunks = hybrid_search(
        collection_name, 
        query="billed amount charge price claim status code denial rejection reason service date Clause 2.2 waiting period", 
        n_results=3, 
        where={"doc_type": "bill"}
    )
    
    # Ensure coverage clauses, exclusion clauses, waiting period clauses, and exception clauses are retrieved together
    policy_chunks = state.get("retrieved_policy_chunks")
    if not policy_chunks:
        # Fallback to query
        policy_general_chunks = hybrid_search(
            collection_name,
            query="policy issue date effective date inception date waiting period Clause 2.2 exclusion period 01 Jan 2022 24 months",
            n_results=4,
            where={"doc_type": "policy"}
        )
        policy_chunks = policy_general_chunks
        state["retrieved_policy_chunks"] = policy_chunks
        
    report_text = "\n\n".join(report_chunks)
    bill_text = "\n\n".join(bill_chunks)
    policy_text = "\n\n".join(policy_chunks)
    
    # Debug logging for retrieved chunks
    print(f"\n===== RETRIEVED CHUNKS FOR {node_name.upper()} =====")
    for idx, chunk in enumerate(report_chunks + bill_chunks + policy_chunks):
        print(f"Chunk {idx+1}:\n{chunk[:300]}...\n")
    print("=====================================================\n")
    
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
        f"Policy Excerpts:\n{policy_text}\n\n"
        f"Hospital Bill Excerpts:\n{bill_text}\n\n"
        f"Doctor's Report Excerpts:\n{report_text}"
    )

    # Extract exact facts using Groq (evidence-first preservation & validation)
    extract_prompt = (
        "You are an insurance claim data extractor. Your task is to extract exact dates and facts "
        "from the provided documents. Do not calculate anything, do not assume, do not make up any numbers, "
        "and do not invent any dates. For every fact or clause extracted, you MUST cite the exact text segment "
        "supporting this fact. If a value is not explicitly stated, return null.\n\n"
        "Guidance on Strict Clause Wording:\n"
        "- Distinguish between recommendations (e.g. 'recommended', 'should', 'normally required', 'suggested') "
        "and mandatory exclusions/conditions (e.g. 'mandatory', 'required', 'must', 'exclusion'). Do not interpret "
        "recommendations as mandatory exclusions or restrictions.\n"
        "- Identify any emergency exceptions or medical necessity exceptions in the policy.\n\n"
        "Respond ONLY in this JSON format:\n"
        "{\n"
        '  "policy_period_start_date": "Current policy period/renewal start date or null",\n'
        '  "original_inception_date": "Original policy inception/first issued date or null",\n'
        '  "waiting_period": "Waiting period duration (e.g. 24 months, 2 years) or null",\n'
        '  "waiting_period_clause": "Clause identifier and exact text of waiting period clause, or null",\n'
        '  "coverage_clauses": [\n'
        '    {\n'
        '      "clause_id": "clause identifier or null",\n'
        '      "clause_text": "exact text of coverage clause",\n'
        '      "type": "mandatory" | "recommended" | "optional"\n'
        '    }\n'
        '  ],\n'
        '  "exclusion_clauses": [\n'
        '    {\n'
        '      "clause_id": "clause identifier or null",\n'
        '      "clause_text": "exact text of exclusion clause",\n'
        '      "type": "mandatory" | "recommended" | "optional",\n'
        '      "applies_to": "what treatment or condition this exclusion applies to"\n'
        '    }\n'
        '  ],\n'
        '  "emergency_exceptions": "exact text of any emergency or exception clauses found, or null",\n'
        '  "treatment_date": "Surgery or treatment date (e.g. 10 Aug 2025) or null",\n'
        '  "rejection_reason": "Stated reason why the claim was denied/rejected from the bill or denial letter, or null",\n'
        '  "medical_necessity_findings": "exact text of medical necessity findings from doctor report, or null"\n'
        "}\n"
        "Do not include any other text."
    )
    
    extracted_facts = call_groq_json(extract_prompt, user_message, max_tokens=1024)
    print("DEBUG: Extracted facts from Groq:", extracted_facts)
    
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
    surgery_date_str = get_case_insensitive(extracted_facts, "treatment_date")
    if not surgery_date_str:
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
            # Check other reasons via LLM on the structured facts only
            eval_prompt = (
                "You are an expert claims dispute auditor. Analyze the following extracted structured facts.\n"
                "Determine if there is a genuine contradiction (mismatch) between the policy terms and the insurer's rejection.\n\n"
                "Guidelines:\n"
                "1. Prove a contradiction before setting mismatch_found to true. A contradiction means the policy explicitly covers the treatment (or has satisfied terms) and the rejection violates this text.\n"
                "2. Absence of evidence is not evidence of contradiction. If documents are missing or silent on a requirement, do not assume a contradiction exists.\n"
                "3. Strict Clause Wording: Distinguish between recommendations (e.g., 'recommended', 'should', 'normally required') and mandatory conditions (e.g. 'mandatory', 'required', 'must'). Do not convert recommendations into exclusions.\n"
                "4. Evidence Validation: For your decision, you MUST cite the exact clause or supporting text from the context. If you cannot cite a specific clause proving the rejection is wrongful, mismatch_found must be false.\n"
                "5. Do not invent any facts, dates, waiting periods, clauses, or exclusions. If evidence is missing, state it is missing, do not guess.\n\n"
                "Respond ONLY in this JSON format:\n"
                "{\n"
                '  "mismatch_found": true or false,\n'
                '  "misapplied_clause": "exact name or text of the misapplied clause, or null if none",\n'
                '  "explanation": "detailed chronological explanation of the decision, referencing specific facts, dates, and exact clause citations"\n'
                "}\n"
                "Do not include any other text."
            )
            eval_res = call_groq_json(eval_prompt, str(extracted_facts), max_tokens=512)
            mismatch_found = bool(get_case_insensitive(eval_res, "mismatch_found", False))
            misapplied_clause = get_case_insensitive(eval_res, "misapplied_clause")
            explanation = get_case_insensitive(eval_res, "explanation", "")
    else:
        # General case (e.g. missing dates) - evaluate via LLM on the structured facts only
        eval_prompt = (
            "You are an expert claims dispute auditor. Analyze the following extracted structured facts.\n"
            "Determine if there is a genuine contradiction (mismatch) between the policy terms and the insurer's rejection.\n\n"
            "Guidelines:\n"
            "1. Prove a contradiction before setting mismatch_found to true. A contradiction means the policy explicitly covers the treatment (or has satisfied terms) and the rejection violates this text.\n"
            "2. Absence of evidence is not evidence of contradiction. If documents are missing or silent on a requirement, do not assume a contradiction exists.\n"
            "3. Strict Clause Wording: Distinguish between recommendations (e.g., 'recommended', 'should', 'normally required') and mandatory conditions (e.g. 'mandatory', 'required', 'must'). Do not convert recommendations into exclusions.\n"
            "4. Evidence Validation: For your decision, you MUST cite the exact clause or supporting text from the context. If you cannot cite a specific clause proving the rejection is wrongful, mismatch_found must be false.\n"
            "5. Do not invent any facts, dates, waiting periods, clauses, or exclusions. If evidence is missing, state it is missing, do not guess.\n\n"
            "Respond ONLY in this JSON format:\n"
            "{\n"
            '  "mismatch_found": true or false,\n'
            '  "misapplied_clause": "exact name or text of the misapplied clause, or null if none",\n'
            '  "explanation": "detailed chronological explanation of the decision, referencing specific facts, dates, and exact clause citations"\n'
            "}\n"
            "Do not include any other text."
        )
        eval_res = call_groq_json(eval_prompt, str(extracted_facts), max_tokens=512)
        mismatch_found = bool(get_case_insensitive(eval_res, "mismatch_found", False))
        misapplied_clause = get_case_insensitive(eval_res, "misapplied_clause")
        explanation = get_case_insensitive(eval_res, "explanation", "")

    # Populate structured facts object
    structured_facts_dict = {
        "original_inception_date": original_inception_str,
        "policy_period_start_date": policy_period_start_str,
        "waiting_period": waiting_period_str,
        "waiting_period_clause_text": wp_clause,
        "coverage_clauses_text": get_case_insensitive(extracted_facts, "coverage_clauses", []),
        "exclusion_clauses_text": get_case_insensitive(extracted_facts, "exclusion_clauses", []),
        "emergency_exceptions_text": get_case_insensitive(extracted_facts, "emergency_exceptions"),
        "rejection_reason": rejection_reason_str,
        "treatment_date": surgery_date_str,
        "medical_necessity_findings_text": get_case_insensitive(extracted_facts, "medical_necessity_findings")
    }
    state["structured_facts"] = structured_facts_dict

    state["mismatch_found"] = mismatch_found
    state["misapplied_clause"] = misapplied_clause
    state["mismatch_explanation"] = explanation
    
    # Store for debug logging
    state["policy_start_date"] = policy_start_str
    state["waiting_period"] = waiting_period_str
    state["waiting_period_completion_date"] = wp_completion.strftime('%d %b %Y') if wp_completion else "N/A"
    state["surgery_date"] = surgery_date_str
    state["coverage_status"] = treatment_covered_str

    # Preserve structured facts in individual state fields for backward compatibility
    state["original_inception_date"] = original_inception_str
    state["policy_period_start_date"] = policy_period_start_str
    state["waiting_period_clause_text"] = wp_clause
    state["coverage_clauses_text"] = get_case_insensitive(extracted_facts, "coverage_clauses", [])
    state["exclusion_clauses_text"] = get_case_insensitive(extracted_facts, "exclusion_clauses", [])
    state["emergency_exceptions_text"] = get_case_insensitive(extracted_facts, "emergency_exceptions")
    state["medical_necessity_findings_text"] = get_case_insensitive(extracted_facts, "medical_necessity_findings")
    
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
    structured_facts = state.get("structured_facts")
    
    # If structured_facts doesn't exist, we fall back to assembling it from individual state fields
    if not structured_facts:
        structured_facts = {
            "original_inception_date": state.get("original_inception_date"),
            "policy_period_start_date": state.get("policy_period_start_date"),
            "waiting_period": state.get("waiting_period"),
            "waiting_period_clause_text": state.get("waiting_period_clause_text"),
            "coverage_clauses_text": state.get("coverage_clauses_text", []),
            "exclusion_clauses_text": state.get("exclusion_clauses_text", []),
            "emergency_exceptions_text": state.get("emergency_exceptions_text"),
            "rejection_reason": state.get("extracted_info", {}).get("rejection_reason") if state.get("extracted_info") else None,
            "treatment_date": state.get("surgery_date"),
            "medical_necessity_findings_text": state.get("medical_necessity_findings_text")
        }
        
    system_prompt = (
        "You are an expert insurance dispute coordinator. Your job is to analyze the structured facts of a claim "
        "and assess semantic evidence and reasoning for each of the following 7 categories. Do not calculate any "
        "numerical scores; the final score will be calculated deterministically in Python based on your classification.\n\n"
        "Categories to evaluate:\n"
        "1. Policy Coverage Support:\n"
        "   - Classification: 'covered' (policy explicitly covers), 'ambiguous' (wording is ambiguous/unclear), or 'excluded' (clearly excluded)\n"
        "2. Rejection Validity:\n"
        "   - Classification: 'invalid' (insurer rejection contradicts policy or misapplies guidelines), 'ambiguous', or 'valid' (clearly valid denial)\n"
        "3. Waiting Period Compliance:\n"
        "   - Classification: 'satisfied' (waiting period completed or not applicable), or 'violated' (treatment occurred during waiting period)\n"
        "4. Coverage Strength / Exclusions:\n"
        "   - Classification: 'no_exclusions' (no exclusions apply), 'ambiguous_exclusions' (exclusions are suggestive/unclear), or 'has_exclusions' (clear exclusions apply)\n"
        "5. Medical Necessity:\n"
        "   - Classification: 'strong' (explicitly supported by doctor with clear clinical findings), 'moderate', or 'weak_or_missing'\n"
        "6. Documentation Quality:\n"
        "   - Classification: 'complete' (all key documents, dates, and amounts present), 'incomplete_minor', or 'incomplete_major' (critical dates/clauses missing)\n"
        "7. Clause Contradiction Severity:\n"
        "   - Classification: 'severe' (direct contradiction between policy and denial), 'moderate', or 'none'\n\n"
        "Guidelines:\n"
        "- Distinguish carefully between recommended guidelines and mandatory requirements. Do not convert recommendations into mandatory exclusions.\n"
        "- Do not guess or invent any details. If evidence is missing, choose the appropriate classification and state that it is missing.\n"
        "- Provide clear evidence citations for all classifications.\n\n"
        "Respond ONLY in this JSON format:\n"
        "{\n"
        '  "policy_coverage_support": "covered" | "ambiguous" | "excluded",\n'
        '  "policy_coverage_support_reason": "explanation citing exact clause text",\n'
        '  "rejection_validity": "invalid" | "ambiguous" | "valid",\n'
        '  "rejection_validity_reason": "explanation citing exact rejection and policy text",\n'
        '  "waiting_period_compliance": "satisfied" | "violated",\n'
        '  "waiting_period_compliance_reason": "explanation referencing inception and treatment dates",\n'
        '  "coverage_strength": "no_exclusions" | "ambiguous_exclusions" | "has_exclusions",\n'
        '  "coverage_strength_reason": "explanation citing exact exclusion clauses",\n'
        '  "medical_necessity": "strong" | "moderate" | "weak_or_missing",\n'
        '  "medical_necessity_reason": "explanation citing doctor report medical necessity findings",\n'
        '  "documentation_quality": "complete" | "incomplete_minor" | "incomplete_major",\n'
        '  "documentation_quality_reason": "explanation of what documents/dates are present or missing",\n'
        '  "contradiction_severity": "severe" | "moderate" | "none",\n'
        '  "contradiction_severity_reason": "explanation of any direct contradiction between rejection and policy/report",\n'
        '  "evidence_helping_patient": ["patient-supporting point 1 with citation", "patient-supporting point 2 with citation"],\n'
        '  "evidence_helping_insurer": ["insurer-supporting point 1 with citation", "insurer-supporting point 2 with citation"],\n'
        '  "points_added_reasons": ["reason 1 for points added based on facts"],\n'
        '  "points_deducted_reasons": ["reason 1 for points deducted based on facts"]\n'
        "}\n"
        "Do not include any other text."
    )
        
    user_message = (
        f"STRUCTURED FACTS EXTRACTED FROM DOCUMENTS:\n"
        f"{structured_facts}\n\n"
        f"MISMATCH ANALYSIS FINDINGS:\n"
        f"- Mismatch Found: {mismatch_found}\n"
        f"- Misapplied Clause: {state.get('misapplied_clause')}\n"
        f"- Mismatch Explanation: {state.get('mismatch_explanation')}\n"
    )
    
    result = call_groq_json(system_prompt, user_message, max_tokens=1024)
    
    # Deterministic Python Scoring Logic
    policy_support_val = result.get("policy_coverage_support", "ambiguous").lower().strip()
    rejection_val = result.get("rejection_validity", "ambiguous").lower().strip()
    waiting_val = result.get("waiting_period_compliance", "satisfied").lower().strip()
    coverage_val = result.get("coverage_strength", "ambiguous_exclusions").lower().strip()
    necessity_val = result.get("medical_necessity", "weak_or_missing").lower().strip()
    doc_val = result.get("documentation_quality", "incomplete_minor").lower().strip()
    contradiction_val = result.get("contradiction_severity", "none").lower().strip()

    # Apply python overrides for a waiting period violation
    # If Python waiting period checks determined a violation, override the LLM classifications to guarantee a low score
    policy_start_str = state.get("policy_start_date")
    waiting_period_str = state.get("waiting_period")
    wp_completion_str = state.get("waiting_period_completion_date")
    surgery_date_str = state.get("surgery_date")
    
    import re
    from datetime import datetime
    def parse_date(date_str: str) -> Optional[datetime]:
        if not date_str or date_str == "N/A":
            return None
        date_str = date_str.strip()
        formats = ["%d %b %Y", "%d %B %Y", "%d-%b-%Y", "%d-%B-%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y", "%b %Y", "%B %Y"]
        clean_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
        clean_str = clean_str.replace(".", "")
        clean_str = re.sub(r'\s+', ' ', clean_str)
        clean_str = re.sub(r'^[^\w]+|[^\w]+$', '', clean_str)
        for fmt in formats:
            try:
                return datetime.strptime(clean_str, fmt)
            except ValueError:
                continue
        return None

    policy_start = parse_date(policy_start_str)
    surgery_dt = parse_date(surgery_date_str)
    wp_completion = parse_date(wp_completion_str)
    
    waiting_period_violation = False
    if surgery_dt and wp_completion:
        if surgery_dt < wp_completion:
            waiting_period_violation = True

    if waiting_period_violation:
        print("PYTHON SCORING OVERRIDE: Waiting period violation detected. Enforcing weak case parameters.")
        policy_support_val = "excluded"
        rejection_val = "valid"
        waiting_val = "violated"
        coverage_val = "has_exclusions"
        contradiction_val = "none"
        mismatch_found = False
        state["mismatch_found"] = False
        state["mismatch_explanation"] = (
            f"The policy started on {policy_start_str} with a waiting period of {waiting_period_str}. "
            f"The waiting period was completed on {wp_completion_str}. "
            f"The surgery occurred on {surgery_date_str}, which is before the waiting period was completed. "
            f"Therefore, the insurer's rejection is valid according to the policy terms."
        )

    # Point mappings
    policy_support_score = 30 if "covered" in policy_support_val else (15 if "ambiguous" in policy_support_val else 0)
    rejection_score = 20 if "invalid" in rejection_val else (10 if "ambiguous" in rejection_val else 0)
    waiting_score = 15 if "satisfied" in waiting_val or "not_applicable" in waiting_val or "not applicable" in waiting_val else 0
    coverage_score = 15 if "no_exclusions" in coverage_val or "no exclusion" in coverage_val else (7 if "ambiguous_exclusions" in coverage_val or "ambiguous" in coverage_val else 0)
    necessity_score = 10 if "strong" in necessity_val else (5 if "moderate" in necessity_val else 0)
    doc_score = 10 if "complete" in doc_val and "incomplete" not in doc_val else (5 if "incomplete_minor" in doc_val or "minor" in doc_val else 0)
    contradiction_score = 10 if "severe" in contradiction_val else (5 if "moderate" in contradiction_val else 0)

    # Sum category scores
    final_score = (
        policy_support_score +
        rejection_score +
        waiting_score +
        coverage_score +
        necessity_score +
        doc_score +
        contradiction_score
    )
    final_score = min(max(final_score, 0), 100)

    # Case strength threshold mapping (retains requested categories and logic)
    if final_score <= 35:
        strength = "weak"
    elif final_score <= 65:
        strength = "moderate"
    else:
        strength = "strong"

    # Construct score reasoning markdown
    reasoning_md = (
        f"### Dispute Score: {final_score} / 100\n"
        f"**Case Strength**: {strength.upper()}\n\n"
        f"#### Category Point Breakdown\n"
        f"- **Policy Coverage Support**: {policy_support_score} / 30 (Assessment: *{policy_support_val}*)\n"
        f"  *Reasoning*: {result.get('policy_coverage_support_reason', 'N/A')}\n"
        f"- **Rejection Validity**: {rejection_score} / 20 (Assessment: *{rejection_val}*)\n"
        f"  *Reasoning*: {result.get('rejection_validity_reason', 'N/A')}\n"
        f"- **Waiting Period Compliance**: {waiting_score} / 15 (Assessment: *{waiting_val}*)\n"
        f"  *Reasoning*: {result.get('waiting_period_compliance_reason', 'N/A')}\n"
        f"- **Coverage Strength / Exclusions**: {coverage_score} / 15 (Assessment: *{coverage_val}*)\n"
        f"  *Reasoning*: {result.get('coverage_strength_reason', 'N/A')}\n"
        f"- **Medical Necessity**: {necessity_score} / 10 (Assessment: *{necessity_val}*)\n"
        f"  *Reasoning*: {result.get('medical_necessity_reason', 'N/A')}\n"
        f"- **Documentation Completeness**: {doc_score} / 10 (Assessment: *{doc_val}*)\n"
        f"  *Reasoning*: {result.get('documentation_quality_reason', 'N/A')}\n"
        f"- **Contradiction Severity**: {contradiction_score} / 10 (Assessment: *{contradiction_val}*)\n"
        f"  *Reasoning*: {result.get('contradiction_severity_reason', 'N/A')}\n\n"
        f"#### Evidence Helping the Patient\n"
    )
    
    for p in result.get("evidence_helping_patient", []):
        reasoning_md += f"- {p}\n"
    if not result.get("evidence_helping_patient"):
        reasoning_md += "- No specific evidence helping the patient identified.\n"
        
    reasoning_md += "\n#### Evidence Helping the Insurer\n"
    for p in result.get("evidence_helping_insurer", []):
        reasoning_md += f"- {p}\n"
    if not result.get("evidence_helping_insurer"):
        reasoning_md += "- No specific evidence helping the insurer identified.\n"
        
    reasoning_md += "\n#### Points Added Reasons\n"
    for p in result.get("points_added_reasons", []):
        reasoning_md += f"- {p}\n"
    if not result.get("points_added_reasons"):
        reasoning_md += "- No points added reasons documented.\n"
        
    reasoning_md += "\n#### Points Deducted Reasons\n"
    for p in result.get("points_deducted_reasons", []):
        reasoning_md += f"- {p}\n"
    if not result.get("points_deducted_reasons"):
        reasoning_md += "- No points deducted reasons documented.\n"

    state["dispute_score"] = final_score
    state["strength"] = strength
    state["score_reasoning"] = reasoning_md
    
    # Debug logging in backend logs
    print("================== DISPUTE REASONING AUDIT LOG ==================")
    print(f"Policy Start Date: {state.get('policy_start_date')}")
    print(f"Waiting Period: {state.get('waiting_period')}")
    print(f"Waiting Period Completion Date: {state.get('waiting_period_completion_date')}")
    print(f"Surgery Date: {state.get('surgery_date')}")
    print(f"Coverage Status: {state.get('coverage_status')}")
    print(f"Mismatch Found: {mismatch_found}")
    print(f"Final Dispute Score: {final_score}")
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
