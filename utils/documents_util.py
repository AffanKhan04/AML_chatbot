import os
import json
import re
from typing import List
from PyPDF2 import PdfReader
from langchain_core.documents import Document
from llm_client import ask


# documents_util.py
# loading each json object into a chunk for vectorization
def load_local_json_to_document(json_path: str) -> List[Document]:
    # loading compliance json
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    documents = []
    for idx, item in enumerate(data):
        # fetching title and description
        description = item.get("Description", "").strip()
        title = item.get("Title", "").strip()

        # ignoring dummy data
        if (
            not description
            or "lorem ipsum" in description.lower()
            or len(description.strip()) < 10
        ):
            continue

        # creating content and metadata
        page_content = f"{title}\n\n{description}"
        metadata = {
            "complianceRuleID": item.get("ComplianceRuleID", ""),
            "CreatedOn": item.get("CreatedOn", ""),
            "title": title,
            "chunk_id": idx,
            "source": "Circular/json",
        }
        documents.append(Document(page_content=page_content, metadata=metadata))
    return documents


# actual convertor pdf to text
def extract_text_from_pdf(path: str) -> str:
    reader = PdfReader(path)
    return "\n".join(
        [page.extract_text() for page in reader.pages if page.extract_text()]
    )


# converting pdf into text   (FILENAME) CONTENT (EOF)
def prepare_files_for_llm(pdf_paths: List[str]) -> str:
    full_text = ""
    for path in pdf_paths:
        filename = os.path.basename(path)
        text = extract_text_from_pdf(path)
        full_text += f"\n<<FILE:{filename}>>\n{text.strip()}\n<<END_OF_FILE>>\n"
        return full_text


# manual chunking for AML first document
def manually_chunk_pdf(path: str) -> list[Document]:
    reader = PdfReader(path)
    full_text = "\n".join(
        page.extract_text() for page in reader.pages if page.extract_text()
    )
    documents = []
    # Extract Acronym section
    acronyms_match = re.search(
        r"ACRONYMS\s*\n(.*?)(?=\n*DEFINITIONS\s*\n)",
        full_text,
        re.DOTALL | re.IGNORECASE,
    )
    if acronyms_match:
        acronym_text = acronyms_match.group(0).strip()
        documents.append(
            Document(
                page_content=acronym_text,
                metadata={"section": "Acronyms", "Chunk_id": 0},
            )
        )
    # Extract definition Section
    definition_match = re.search(
        r"DEFINITIONS\s*\n(.*?)(?=\n*REGULATION\s*[-–]?\s*\d+\s*\n)",
        full_text,
        re.DOTALL | re.IGNORECASE,
    )
    if definition_match:
        definition_text = "DEFINITIONS\n" + definition_match.group(1).strip()
        documents.append(
            Document(
                page_content=definition_text,
                metadata={"section": "Definitions", "chink_id": 1},
            )
        )

    # make a seperate chunk for each regulation
    pattern = re.compile(
        r"(REGULATION\s*[-–]?\s*(\d+)\s*\n([^\n]+)\n)(.*?)(?=(REGULATION\s*[-–]?\s*\d+\s*\n|$))",
        re.DOTALL,
    )

    for idx, match in enumerate(pattern.findall(full_text), start=2):
        # for match in pattern.findall(full_text):
        header, reg_number, title, body = match[:4]
        full_content = f"{header}{body}".strip()

        doc = Document(
            page_content=full_content,
            metadata={
                "regulation_number": str(reg_number),
                "title": title.strip(),
                "chunk_id": idx,
                "source": "pdf",
                "filename": "AML Regulations - CL33-Annex-B.pdf",
            },
        )
        documents.append(doc)
    print("documents: ",documents)
    return documents


# function for LLM to insert breakpoints into the text
def insert_breakpoints_with_llm(document_text: str) -> str:
    # prompt for inserting breakpoints
    prompt = f"""
        You are a document chunking assistant.  
        Your goal is to split regulatory, compliance, and licensing documents into logical chunks
        based strictly on their natural structure.

        ### Rules for Breakpoints:
        1. Insert `<<<BREAK>>>` **before each top-level heading**  
        - Examples: "REGULATION - 5", "Section 2: Licensing Criteria", "FAQs", "Application Form", "Definitions", "Acronyms".

        2. For headings with multiple sub-points:
        - If the points are **long or detailed**, split them into **separate chunks per point**.  
        - If the points are **short clauses**, keep them together under the same heading.

        3. For FAQs:
        - Each question and its answer should be **one chunk**.

        4. For special sections:
        - "Table of Contents" → one chunk.  
        - "Definitions" → one chunk.  
        - "Acronyms" → one chunk.  
        - "Forms" or "Tables" → keep entire form/table as a **single chunk**.

        5. Do NOT:
        - Split inside a single sentence.  
        - Split inside a table row.  
        - Over-fragment the document.

        ### Input Format:
        The file will be wrapped like this:
        <<FILE:filename.pdf>>
        ...document text...
        <<END_OF_FILE>>

        ### Output Format:
        - Return the document text with `<<<BREAK>>>` inserted at correct places.  
        - Do not rewrite or summarize. Only insert `<<<BREAK>>>`.

        Here is the document:
        {document_text}
    """
    # ans = ask_deepseek(prompt)
    ans=ask(prompt)
    print("✅ deepseek Breakpoints: ", ans)
    return ans


# function for breaking text on the basis of <<<BREAK>>> breakpoint
def parse_llm_chunks(llm_output: str,filename:str) -> List[Document]:
    docs = []
    current_file = "unknown"
    chunks = llm_output.split("<<<BREAK>>>")

    for idx, chunk in enumerate(chunks):
        chunk = chunk.strip()

        # condition for checking null or empty chunk
        if not chunk:
            continue
        # extracting filename
        file_match = re.search(r"<<FILE:(.*?)>>", chunk)

        if file_match:
            current_file = file_match.group(1).strip()

        # Clean chunk text (remove markers)
        chunk_clean = re.sub(r"<<.*?>>", "", chunk).strip()
        
        reg_match = re.search(r"REGULATION\s*[-\u2013]?\s*(\d+)", chunk_clean, re.IGNORECASE)
        point_match = re.search(r"^\s*([0-9ivxIVX]+)[.)]\s", chunk_clean)  # handles 1. ii. etc
        title_match = re.search(r"REGULATION\s*[-\u2013]?\s*\d+\s*\n([^\n]+)", chunk_clean, re.IGNORECASE)

        # creating metadata
        metadata = {"filename": filename, "chunk_id": idx}

        if reg_match:
            metadata["regulation_number"] = reg_match.group(1)
        if point_match:
            metadata["point_number"] = point_match.group(1)
        # if title_match:
        # metadata["section_title"] = title_match.group().strip()
        lines = chunk_clean.split("\n")
        metadata["section_title"] = lines[0].strip()
        docs.append(Document(page_content=chunk_clean, metadata=metadata))

    return docs



def process_single_file(pdf_path: str) -> List[Document]:
         # """Process one PDF file into chunks (manual for AML, LLM-based otherwise)."""
    all_chunks = []
    if "AML Regulations - CL33-Annex-B.pdf" in pdf_path:
        print(f"📘 Using manual chunking for: {pdf_path}")
        # all_chunks.extend(manually_chunk_pdf(pdf_path))
        return manually_chunk_pdf(pdf_path)
    else:
        print(f"🔄 Extracting and preparing text from {pdf_path}...")
        filename = os.path.basename(pdf_path)
        text = extract_text_from_pdf(pdf_path)
        wrapped_text = f"<<FILE:{filename}>>\n{text}\n<<END_OF_FILE>>"

        # Ask LLM for breakpoints
        print("🧠 Asking LLM to insert breakpoints...")
        llm_output = insert_breakpoints_with_llm(wrapped_text)
        print(f"🔹 Breakpoint preview for {filename}:\n\n{llm_output[:500]}...\n")

        # Parse into chunks
        print("📦 Parsing LLM output into chunks with metadata...")
        all_chunks.extend(parse_llm_chunks(llm_output,filename))

        return all_chunks
