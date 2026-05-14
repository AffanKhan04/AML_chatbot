from llm_client import ask
from Agents.query_understanding_agent import parse_query_with_llm
from Agents.retriever_agent import retrieve_document
from utils.guardrails_util import validate_query_with_guardrails
from utils.chroma_utils import save_chat_turn , get_session_memory
import json,re
import uuid

last_llm_response=None
last_context=None
requirements=None

def generate_actionable_task():
    global last_context
    global requirements
    
    mapped_frequency = ["Monthly", "Quarterly", "Annually", "Ongoing", "Ad-hoc"]
    mapped_department = ["Compliance", "Audit", "Risk", "IT", "HR", "Operations"]
    mapped_activity_priority = ["High", "Medium", "Low"]
    
    prompt = f"""
    You are a compliance task generation expert. 
    You are provided with:
    1. **The original regulation/circular context** — for deeper understanding.
    2. **A list of AML/compliance requirements** extracted from that context.

    Your job:
    - For EACH requirement, generate a **maximum of 3 actionable tasks** needed to meet the requirement.
    - Each requirement’s tasks should be grouped under a heading: "Tasks for: <requirement title>".
    - Tasks must be **specific and compliance-focused**, not generic.
    - Use the context only when necessary to clarify the requirement.

    **For each task, provide:**
    - "Task": A short, specific action (max 80 characters)
    - "Description": Concise explanation (max 25 words)
    - "Frequency": Choose from {mapped_frequency} if possible, else infer
    - "ActivityPriority": Choose from {mapped_activity_priority} if possible, else infer
    - "Department": Choose from {mapped_department} if possible, else infer
    - "HowTo": Clear steps to perform the task (max 40 words)

    **Rules:**
    - Return no more than 2 tasks per requirement. 
    - If a requirement is unclear, return only 1 task.
    - Keep JSON size compact and valid.
    - Use values from requirements JSON (Frequency, Department) if already provided.
    - Output **only valid JSON**. No extra text, markdown, or comments.

    **Expected JSON format:**
    {{
        "tasks": [
            {{
                "RequirementTitle": "...",
                "Tasks": [
                    {{
                        "Task": "...",
                        "Description": "...",
                        "Frequency": "...",
                        "ActivityPriority": "...",
                        "Department": "...",
                        "HowTo": "..."
                    }}
                ]
            }}
        ]
    }}

    ---
    Context:
    {last_context}

    Requirements:
    {json.dumps(requirements, ensure_ascii=False)}
    """
    
    # structured_response = ask_deepseek(prompt)
    structured_response = ask(prompt)
    # structured_response=ask_ollama(prompt)
    structured_response = re.sub(r"```json|```", "", structured_response).strip()
    
    try:
        data = json.loads(structured_response)
        if "tasks" in data:
            return {"response": data}
        else:
            return {"error": "No 'tasks' key found in response.", "raw": structured_response}
    except Exception as e:
        return {
            "error": "Failed to parse LLM response into JSON.",
            "raw": structured_response,
            "exception": str(e)
        }



def extract_requirements():
    global last_llm_response
    global last_context
    global requirements

    print("last_llm_response: ", last_llm_response)
    if not last_llm_response:
        return {"error": "No previous LLM response found"}

    # Frequency and department options
    mapped_frequency = ["Monthly", "Quarterly", "Annually", "Ongoing", "Ad-hoc"]
    mapped_department = ["Compliance", "Audit", "Risk", "IT", "HR", "Operations"]

    #prompt
    prompt = f"""
    You are a compliance analyst working with various regulatory sources, including AML regulations, SBP circulars, and compliance rule documents.

    You are given:
    1. A **context** that contains one or more AML/circular chunks. Each chunk starts with a **header metadata line** like:
    [filename: ..., regulation_number: ..., point_number: ..., title: ...]
    Followed by the actual regulation or circular **text**.

    2. A **summary or interpretation** of the content (LLM response).

    ---

    Your task is to extract **major AML implementation requirements** and return them as structured JSON.

    ---

    For each requirement, extract:

    - "Title":
    - If metadata includes a `title`, use it.
    - Otherwise, generate a short (max 15 words) title based on the Description.

    - "Description":
    - Must be a **verbatim sentence** or regulation from the context. Do NOT summarize or rewrite.

    - "Frequency":
    - Choose from: {mapped_frequency}, or use your own if more appropriate.

    - "Department":
    - Choose from: {mapped_department}, or suggest based on the requirement.

    - "Reference":
    - Try to extract a **regulation number** (e.g., "1(3)", "4(1)") from the actual **text of the context's metadata**.nd use that "Regulation number"
    - If no regulation number is present, look for a **point number** (e.g., "Point 7", "Para 2") from the context's metadata and use that "Point number"
    - Else if `title` exists and filename is missing/null → Use title
    - Else → "Unspecified"

    - "filename":
    - Use from metadata if available.
    - If missing/null → set as "SBP Circular/Law"

    Return only **clean JSON** in the format below — no explanations, no markdown, no headings:

    {{
    "requirements": [
    {{
    "Title": "...",
    "Description": "...",
    "Frequency": "...",
    "Department": "...",
    "Reference": "...",
    "filename": "..."
    }}
    ]
    }}

    Here is the content to analyze:

    Context:
    {last_context}

    LLM Summary:
    {last_llm_response}
    """

    # Ask LLM
    # structured_response = ask_deepseek(prompt)
    structured_response = ask(prompt)
    # structured_response=ask_ollama(prompt)
    print("structured_response: ", structured_response)

    # Clean LLM output
    structured_response = re.sub(r"```json|```", "", structured_response).strip()

    try:
        data = json.loads(structured_response)

        if "requirements" in data:
            #filter out malformed entries
            valid_reqs = [
                req for req in data["requirements"]
                if all(k in req for k in ("Title", "Description", "Frequency", "Department", "Reference", "filename"))
            ]
            requirements=valid_reqs
            return {"response": {"requirements": valid_reqs}}
        else:
            return {"error": "No 'requirements' key found in response.", "raw": structured_response}
    except Exception as e:
        return {
            "error": "Failed to parse LLM response into JSON.",
            "raw": structured_response,
            "exception": str(e)
        }

def build_context_with_metdata(docs)->str:
    """
    Build a combined string of metadata headers + content from retrieved documents.
    """
    context_chunks = []
    for doc in docs:
        content = doc.page_content.strip()
        metadata = doc.metadata or {}

        # Safely get values
        filename = metadata.get("filename", "")
        regulation_number = metadata.get("regulation_number", "")
        point_number = metadata.get("point_number", "")
        title = metadata.get("title", "")

        # Create metadata header
        metadata_header = (
            f"[Filename: {filename}, Regulation: {regulation_number}, "
            f"Point: {point_number}, Title: {title}]"
        )
        context_chunks.append(f"{metadata_header}\n{content}")

    return "\n\n".join(context_chunks)

def ask_llm(query:str,chat_id:str=None):
    ("In pipeline")
    global last_llm_response
    global last_context
    
    
    if not chat_id:
        chat_id=str(uuid.uuid4())
        
    #step 0: converting user query into LLM understanding form     
    parsed = parse_query_with_llm(query)
    print("✅Parsed Query:", parsed)
    
    # Step 1: Retrieve context
    docs,similarity_scores =retrieve_document(query,parsed)
    
    
    #step 2: Convert context into meaningful form
    context=build_context_with_metdata(docs)
    last_context=context
    print("✅context: "," ".join(context.split()[:50]))
    
    memory=get_session_memory(chat_id,k=3)
    history_text=memory.load_memory_variables({}).get("history","")
    print("✅ history: ",history_text)
    #step 3: Validate query against content policies via prompt-based guardrails
    try:
        validate_query_with_guardrails(query, context, history_text)
    except Exception as e:
        return {
            "result": f"❌ Query rejected: {str(e)}"
        }
        
        
    print("query: ",query)
    
    
    save_chat_turn(chat_id,"user",query)
    memory.chat_memory.add_user_message(query)
    
    prompt = f"""
    You are a compliance assistant for a bank. Your role is to understand user queries and respond to them as a the head of the compliance department, assisting users on the rules and regulations they would need to adhere to 

    Your task is to decide whether the user's latest query is relevant.

    Rules:
    1. First, check if the query is directly answerable from the provided context.
    2. If not, check the chat history:
    - If the query is a natural follow-up or clarification to the previous conversation, you may still answer it.
    - Example: If the last question was about Regulation 5, and now the user asks "What about Regulation 6?", it is a valid follow-up.
    3. If the query is unrelated to both the regulation context and the chat history, strictly reply:
    "I'm sorry, I do not have an answer to that question."

    Always cite the regulation reference wherever applicable and maintain the wording of the original regulation or circular

    ---

    Chat history:
    {history_text}

    Context:
    {context}

    User question:
    {query}

    Now provide your response following the above rules.
    """
    # answer = ask_deepseek(prompt)
    answer=ask(prompt)
    # answer=ask_ollama(prompt)
    last_llm_response=answer
    
    save_chat_turn(chat_id,"assistant",answer)
    memory.chat_memory.add_ai_message(answer)
    
     #step 5: return result to user
    return {"result": answer,"chat_id":chat_id}



# or in detail where needed 