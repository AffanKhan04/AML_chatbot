import json
from llm_client import ask

def parse_query_with_llm(user_query:str)->dict:
    print("IN QUA")
    #prompt for refinig the user given query into LLM meaningful form
    prompt = f"""
    You are a strict query parser for a multi-document regulatory system.

    Your task is to extract:
    - The user's **intent**: one of ["retrieve", "summarize", "compare", "unknown"]
    - Any **regulation numbers**, **point numbers**, or **document titles** mentioned

    Return a JSON with:
    - "intent": The user's intent
    - "references": A list of relevant references (e.g., regulation numbers like "13", point numbers like "7", or partial titles like "Livestock Insurance Scheme")

    Rules:
    - If the query is a joke, poem, casual or irrelevant, mark intent as "unknown"
    - If no references are found, return an empty array for "references"

    Examples:
    User: "Compare Regulation 13 and Regulation 14"  
    → {{ "intent": "compare", "references": ["13", "14"] }}

    User: "Explain point 7 of AML guidelines"  
    → {{ "intent": "retrieve", "references": ["7"] }}

    User: "What does the circular on livestock say?"  
    → {{ "intent": "retrieve", "references": ["Livestock Insurance Scheme"] }}

    User: "Tell me a poem about money"  
    → {{ "intent": "unknown", "references": [] }}

    Now parse:
    User query: "{user_query}"
    Return only a valid JSON object, with no explanation, no markdown, no text before or after.
    """


    # response=ask_deepseek(prompt)
    response=ask(prompt)
    # response=ask_ollama(prompt)
    print("LLM Parsed query response: ",response)
    
    # Clean markdown code block if exists
    if response.startswith("```"):
        response = response.strip().strip("`").replace("json", "", 1).strip()
    try:
       parsed = json.loads(response.strip())
       if isinstance(parsed, dict) and 'intent' in parsed:
            return parsed
    except Exception as e:
        print("❌ JSON parsing error:", e)
        print("⚠️ Raw response:", response)
    return {"intent":"unknown","regulation":[]}
    