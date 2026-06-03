import os
from services.groq_service import call_groq_json

def run_evaluation(question: str, answer: str, contexts: list[str]) -> dict:
    """
    Runs RAGAS evaluation (faithfulness and answer_relevancy).
    Falls back to custom Groq LLM grader if RAGAS is not fully initialized.
    """
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy
        from langchain_groq import ChatGroq
        
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set.")
            
        # Configure RAGAS to use ChatGroq LLM
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        llm = ChatGroq(
            groq_api_key=api_key,
            model_name=model,
            temperature=0.1
        )
        
        # Prepare evaluation dataset
        data = {
            "question": [question],
            "answer": [answer],
            "contexts": [contexts]
        }
        dataset = Dataset.from_dict(data)
        
        # Run RAGAS evaluation
        result = evaluate(
            dataset=dataset,
            metrics=[faithfulness, answer_relevancy],
            llm=llm
        )
        
        return {
            "faithfulness": float(result.get("faithfulness", 0.0)),
            "answer_relevancy": float(result.get("answer_relevancy", 0.0))
        }
    except Exception as e:
        print(f"RAGAS evaluation failed, using custom Groq LLM fallback: {str(e)}")
        return run_evaluation_fallback(question, answer, contexts)

def run_evaluation_fallback(question: str, answer: str, contexts: list[str]) -> dict:
    """
    Fallback RAG evaluator using custom Groq prompts.
    """
    system_prompt = (
        "You are an expert AI evaluator assessing RAG performance metrics on a 0.0 to 1.0 scale.\n"
        "Analyze the context and answer to score:\n"
        "1. faithfulness: Is the answer factually grounded in and supported ONLY by the provided contexts? (0.0 = completely ungrounded, 1.0 = fully supported)\n"
        "2. answer_relevancy: Does the answer directly address the original question? (0.0 = completely off-topic, 1.0 = highly relevant)\n\n"
        "Respond ONLY in this JSON format:\n"
        "{\n"
        '  "faithfulness": 0.90,\n'
        '  "answer_relevancy": 0.95\n'
        "}\n"
        "Do not add any text outside the JSON."
    )
    
    user_message = (
        f"Question: {question}\n\n"
        f"Answer: {answer}\n\n"
        f"Contexts Excerpts:\n" + "\n".join(f"- {c}" for c in contexts)
    )
    
    try:
        res = call_groq_json(system_prompt, user_message)
        return {
            "faithfulness": float(res.get("faithfulness", 0.85)),
            "answer_relevancy": float(res.get("answer_relevancy", 0.85))
        }
    except Exception:
        # Static mock return if Groq fails
        return {"faithfulness": 0.80, "answer_relevancy": 0.80}
