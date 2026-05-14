from guardrails import Guard
from guardrails.hub import DetectJailbreak, LlamaGuard7B, BanList
from dotenv import load_dotenv
import os
load_dotenv()  # This loads the .env file


def validate_query_with_guardrails(query: str, context: str , history_text:str):
    # 1. Jailbreak detection
    # Guard().use(DetectJailbreak(on_fail="exception")).validate(query)
    # print("✅ Passed Jail Break Guardrail")

    # 2. Harmful/illegal content classification
    Guard().use(LlamaGuard7B(
        # categories=["non_violent_crimes", "financial_crime"],
        policies=[LlamaGuard7B.POLICY__NO_ILLEGAL_DRUGS , LlamaGuard7B.POLICY__NO_VIOLENCE_HATE, LlamaGuard7B.POLICY__NO_SEXUAL_CONTENT, LlamaGuard7B.POLICY__NO_CRIMINAL_PLANNING, LlamaGuard7B.POLICY__NO_GUNS_AND_ILLEGAL_WEAPONS,LlamaGuard7B.POLICY__NO_ENOURAGE_SELF_HARM],
        on_fail="exception"
    )).validate(query)
    print("✅ Passed Llama Guard Guardrail")
    # 3. Ban list enforcement
    Guard().use(BanList(
        banned_words=[
            'loopholes',
            'launder money',
            'missing elements',
            'bypass AML',
            'exploit SBP rules',
            'weakness in compliance',
            'joke',
            'funny',
            'make me laugh',
            'meme', 
            'humor',
            'story about',
            'poem',
            'lack'
        ],
        max_l_dist=0,
        on_fail="exception"
    )).validate(query)
    print("✅ Passed Ban List Guardrail")

   # 4. Similarity to document context
    # try:
    # Guard().use(SimilarToDocument(
    #     document=f"{expanded_context}\n\nDocument context:\n{context}",
    #     threshold=0.5,
    #     model="all-MiniLM-L6-v2",
    #     on_fail="exception"
    # )).validate(query)
    # print("✅ Passed Similar to document context Guardrail")
    # # except Exception:
    #   # If fails, try evaluating relevance against history + context using LlmRagEvaluator
    #     print("⚠️ Similarity failed, using LlmRagEvaluator on history+context...",os.getenv("OPENAI_API_KEY"))
    #     guard = Guard().use(
    #         LlmRagEvaluator(
    #             eval_llm_prompt_generator=HallucinationPrompt(prompt_name="hallucination_judge_llm"),
    #             llm_evaluator_fail_response="hallucinated",
    #             llm_evaluator_pass_response="factual",
    #             llm_callable="gpt-4o-mini",
    #             on_fail="exception"
    #         )
    #     )
    #     metadata = {
    #         "user_message": query,
    #         "context": f"{context}\n\n{history_context_text}",
    #         "llm_response": query  # treat question as 'response' for relevance check
    #     }
    #     guard.validate(llm_output=query, metadata=metadata)

    return True
