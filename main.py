from fastapi import FastAPI , UploadFile , File , HTTPException
from fastapi.middleware.cors import CORSMiddleware
from rag_pipeline import ask_llm , extract_requirements , generate_actionable_task
from utils.documents_util import process_single_file
from utils.chroma_utils import add_docs_to_chroma , setup_bm25_retriever , list_all_chunks
# from docling_dynamic_document import dynamic_document_vectorization
from typing import Optional
from pydantic import BaseModel
import tempfile
import os
import io
import traceback
import time


#Creating Fast API server
app = FastAPI()

#adding middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AskRequest(BaseModel):
    query:str
    chat_id:Optional[str]=None

#Path setup
json_path = "compliance_rules_clean.json"
persist_dir = "./chroma_db"
pdf_folder = "uploads"


@app.post("/upload_and_vectorize")
async def upload_and_vectorize(file: UploadFile = File(...)):
    try:
        # save uploaded file into uploads/ folder with original filename
        file_path = os.path.join(pdf_folder, file.filename)
        if os.path.exists(file_path):
            return {"detail": f"❌ File {file.filename} already exists."}

        with open(file_path, "wb") as f:
            f.write(await file.read())

        # process & chunk this file
        chunks = process_single_file(file_path)

        # vectorize 
        add_docs_to_chroma(chunks)
        setup_bm25_retriever(chunks)
        return {"detail": f"✅ Successfully vectorized {file.filename}", "chunks_added": len(chunks),"docs:":chunks}

    except Exception as e:
        return {"detail": str(e)}
      
@app.get("/")
async def get_all_chunks(): 
    return list_all_chunks()



#user QA endpoint with chat history logging
@app.post("/ask")
async def ask(data:AskRequest):
    print("In backend chat id is: ",data.chat_id)
    start = time.time()
    outcome = ask_llm(data.query, chat_id=data.chat_id)
    duration = round(time.time() - start, 2)
    print(f"✅ /ask responded in {duration} seconds.")
     # ✅ Log the Q&A here
    # log_qa(query, outcome.get("result"))
    return {"response": outcome.get("result"), "chat_id": outcome.get("chat_id")}

   


#Requirement Generation Endpoint
@app.post("/requirements")
async def requirements():
    start = time.time()
    result = extract_requirements()
    duration = round(time.time() - start, 2)
    print(f"✅ /requirements responded in {duration} seconds.")
    return result

#route to create actionable tasks
@app.post("/actions")
async def actions():
    start = time.time()
    result = generate_actionable_task()
    duration = round(time.time() - start, 2)
    print(f"✅ /actions responded in {duration} seconds.")
    return result

