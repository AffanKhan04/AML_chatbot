from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
import os,shutil,re
from fastapi.responses import JSONResponse
import uuid ,datetime
from langchain_community.chat_message_histories import ChatMessageHistory
class ConversationBufferWindowMemory:
    """Minimal replacement for the removed langchain ConversationBufferWindowMemory."""
    def __init__(self, k=5, return_messages=False, chat_memory=None):
        self.k = k
        self.chat_memory = chat_memory or ChatMessageHistory()

    def load_memory_variables(self, _inputs):
        messages = self.chat_memory.messages[-(self.k * 2):]
        lines = []
        for msg in messages:
            role = "Human" if msg.type == "human" else "AI"
            lines.append(f"{role}: {msg.content}")
        return {"history": "\n".join(lines)}


#initializing embedding model
embeddings=HuggingFaceEmbeddings(model_name='all-MiniLM-L6-v2')
#chroma db directory
persist_dir="./chroma_db"
chat_history_dir="./chroma_chat_history"
bm25_retriever=None


#initializing chroma db 
def initialize_chroma():
    return Chroma(persist_directory=persist_dir ,embedding_function=embeddings)

#add documents to chormadb
def add_docs_to_chroma(docs:list[Document]):
    vectordb=initialize_chroma()
    batch_size = 5000
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i + batch_size]
        vectordb.add_documents(batch)

#initializing bm25 searching
def setup_bm25_retriever(docs:list[Document]):
    global bm25_retriever
    bm25_retriever=BM25Retriever.from_documents(docs)
    bm25_retriever.k=3


#function for deleting chroma directory (if needed)
def clear_chroma():
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)    
        
#List all chunks stored in Chroma
def list_all_chunks():
    vectordb = initialize_chroma()
    results = vectordb.get(include=["metadatas", "documents"])
    
    print(f"📦 Total Chunks in Chroma: {len(results['documents'])}\n")

    chunks=[]
    for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas'])): 
        chunks.append({
            "chunk": f"🔹 Chunk #{i + 1}",
            "content": doc,
            "metadata": meta
        })
         
    return JSONResponse(content={"total_chunks": len(chunks), "chunks": chunks})


def initialize_chat_chroma():
    return Chroma(persist_directory=chat_history_dir,embedding_function=embeddings)

def save_chat_turn(chat_id: str, role: str, text: str):
    chat_collection = initialize_chat_chroma()
    doc = Document(
        page_content=text,
        metadata={
            "chat_id": chat_id,
            "role": role,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    )
    chat_collection.add_documents([doc])
    
def get_chat_history(chat_id:str,limit:int=5):
    chat_collection=initialize_chat_chroma()
    results=chat_collection.get(where={"chat_id":chat_id},include=["metadatas","documents"])
    metadatas=results.get("metadatas",[])
    documents=results.get("documents",[])
    items=[]
    for meta , doc in zip(metadatas,documents):
        items.append((meta,doc))
        
    #sort by time
    items.sort(key=lambda x:x[0].get("timestamp",""))
    return items[-limit:] # last limit chats 
    
_session_memories={}
def rebuild_session_memory_from_chroma(chat_id:str,k:int=5):
    history=get_chat_history(chat_id,limit=k)   
    mem = ConversationBufferWindowMemory(
        k=k,
        return_messages=False,
        chat_memory=ChatMessageHistory()
    )
    
    #add loaded turns in order
    for meta , text in history:
        role=meta.get("role","user")
        if role == "user":
            mem.chat_memory.add_user_message(text)
        else:
            mem.chat_memory.add_ai_message(text)
    _session_memories[chat_id]=mem
    return mem

def get_session_memory(chat_id:str,k:int=5):
    return rebuild_session_memory_from_chroma(chat_id,k)
    