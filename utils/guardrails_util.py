from llm_client import ask

BANNED_PHRASES = [
    'loopholes', 'launder money', 'missing elements', 'bypass AML',
    'exploit SBP rules', 'weakness in compliance', 'joke', 'funny',
    'make me laugh', 'meme', 'humor', 'story about', 'poem', 'lack'
]

_GUARDRAIL_PROMPT = """You are a strict content moderation system for an AML (Anti-Money Laundering) compliance chatbot.

Evaluate the following user query and determine if it violates any of the rules below.

### Rules:
1. No requests related to illegal drugs, drug trafficking, or drug use.
2. No violent, hateful, or discriminatory content.
3. No sexual or explicit content.
4. No criminal planning, money laundering schemes, or financial crime assistance.
5. No requests about illegal weapons, firearms trafficking, or arms dealing.
6. No content that encourages self-harm or suicide.
7. No off-topic or entertainment-based requests (jokes, poems, memes, stories, humor).
8. No requests to bypass, exploit, or find loopholes in AML/CFT regulations.
9. No requests containing these phrases: {banned_phrases}

### Instructions:
- If the query violates ANY rule, respond with exactly: UNSAFE: <brief reason>
- If the query is safe and appropriate for an AML compliance assistant, respond with exactly: SAFE

Respond with ONLY "SAFE" or "UNSAFE: <reason>". No other text.

User query: {query}"""


def validate_query_with_guardrails(query: str, context: str, history_text: str):
    query_lower = query.lower()
    for phrase in BANNED_PHRASES:
        if phrase in query_lower:
            raise ValueError(f"Query contains a banned phrase: '{phrase}'")

    prompt = _GUARDRAIL_PROMPT.format(
        banned_phrases=", ".join(f'"{p}"' for p in BANNED_PHRASES),
        query=query
    )
    result = ask(prompt).strip()

    if result.upper().startswith("UNSAFE"):
        reason = result[result.find(":")+1:].strip() if ":" in result else "Content policy violation"
        raise ValueError(reason)

    return True
