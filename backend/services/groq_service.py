from groq import Groq
import os
import json

_client = None

def get_groq_client() -> Groq:
    """
    Lazily initializes and returns the Groq client.
    """
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set. Please configure it in your environment.")
        _client = Groq(api_key=api_key)
    return _client

def call_groq(system_prompt: str, user_message: str, max_tokens: int = 1024) -> str:
    """
    Calls Groq Chat Completion with llama-3.3-70b-versatile or custom model.
    """
    client = get_groq_client()
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0.1,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content

def call_groq_json(system_prompt: str, user_message: str, max_tokens: int = 1024) -> dict:
    """
    Calls Groq and parses the output as JSON, stripping Markdown backticks if present.
    """
    raw = call_groq(system_prompt, user_message, max_tokens=max_tokens)
    clean = raw.strip()
    
    # Strip markdown code blocks if the model wrapped JSON
    if clean.startswith("```json"):
        clean = clean[7:]
    elif clean.startswith("```"):
        clean = clean[3:]
        
    if clean.endswith("```"):
        clean = clean[:-3]
        
    clean = clean.strip()
    
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        # Secondary parser: extract the first '{' and last '}' substring
        start_idx = clean.find("{")
        end_idx = clean.rfind("}")
        if start_idx != -1 and end_idx != -1:
            json_substr = clean[start_idx:end_idx + 1]
            try:
                return json.loads(json_substr)
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Failed to parse JSON from Groq response: {raw}")
