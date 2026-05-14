from utils.chroma_utils import initialize_chroma , bm25_retriever
from langchain_core.documents import Document

def retrieve_document(user_query:str,parsed_query:dict)-> tuple[list[Document], float]:
    print("IN RA")
    #initializing vector db
    vectordb=initialize_chroma()
    #initialze references and intent
    references=parsed_query.get("references",[])
    print("📌 REFERENCES: ",references)
    intent=parsed_query.get("intent","unknown")
    
    #calculating similarity score
    results_with_scores=vectordb.similarity_search_with_score(user_query,k=1)
    similarity_scores=results_with_scores[0][1] if results_with_scores else 0.0
    print("similarity scores: ",similarity_scores)
    
    # filter based retrieval
    if references:
        all_docs = []
        for ref in references:
            print(f"📌 Searching with reference: {ref}")

            # Try multiple filters based on type of reference
            for filter_key in ["regulation_number", "point_number", "title"]:
                docs = vectordb.similarity_search(user_query, k=3, filter={filter_key: ref})
                if docs:
                    all_docs.extend(docs)
                    break 

        unique_docs = list({doc.page_content: doc for doc in all_docs}.values())
        if unique_docs:
            return unique_docs[:5], similarity_scores
        
    #bm25 retrieval
    if bm25_retriever:
        bm25_docs=bm25_retriever.get_relevant_documents(user_query)
        vector_docs =vectordb.similarity_search(user_query,k=3)
        all_docs={d.page_content: d for d in (bm25_docs + vector_docs)}
        return list(all_docs.values())[:5] , similarity_scores
    
    #normal search
    return vectordb.similarity_search(user_query,k=3) , similarity_scores