# 
from openai import OpenAI
from groq import Groq
from ollama import Client
import os
from dotenv import load_dotenv

load_dotenv()

system_prompt = """
You are Qwen, a senior compliance officer and regulatory advisor for a financial institution.
You specialize in Anti-Money Laundering (AML), Counter Financing of Terrorism (CFT), and related
banking regulations and circulars.

Your responsibility is to ensure every response you provide is:
- Accurate, compliant, and grounded in the given context or chat history.
- Written in a formal, advisory tone as if speaking to junior compliance staff.
- Fact-based and supported by specific regulation numbers or circular references.

When uncertain or when the query is off-topic or lacks relevant information,
respond exactly with: "I'm sorry, I do not have an answer to that question."

Always maintain the regulatory language of the source — do not paraphrase excessively.
"""


# Load provider & keys from env
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def ask(prompt: str) -> str:
    if LLM_PROVIDER == "deepseek":
        # OpenRouter DeepSeek Client
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )
        completion = client.chat.completions.create(
            model="deepseek/deepseek-chat-v3-0324:free",
            messages=[{"role": "user", "content": prompt}],
            extra_headers={
                "HTTP-Referer": "http://localhost",
                "X-Title": "DeepSeekLangChainApp"
            }
        )
        return completion.choices[0].message.content

    elif LLM_PROVIDER == "groq":
        # Groq Client
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_completion_tokens=8192,
            top_p=1,
            stream=True
        )

        full_response = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content
    
        return full_response
    
    elif LLM_PROVIDER=="ollama":
        client=Client(host="http://localhost:11434")
        model_name=os.getenv("OLLAMA_MODEL","smollm2:1.7b")
        print("model name: ",model_name)
        response = client.chat(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
            ]
        )
        return response["message"]["content"]

    else:
        raise ValueError(f"❌ Unsupported LLM provider: {LLM_PROVIDER}")
    
    
    
        
