# import os
# from fastapi import HTTPException
# from langchain_docling import DoclingLoader
# from docling.chunking import HybridChunker
# from langchain_docling.loader import ExportType

# # global chunker
# default_chunker = HybridChunker(tokenizer="sentence-transformers/all-MiniLM-L6-v2")

# UPLOAD_DIR = "uploads"
# os.makedirs(UPLOAD_DIR, exist_ok=True)  # ensure uploads folder exists

# async def dynamic_document_vectorization(file):
#     # ✅ Build full path for uploaded file
#     file_path = os.path.join(UPLOAD_DIR, file.filename)

#     # ✅ If file already exists, stop and return message
#     if os.path.exists(file_path):
#         raise HTTPException(
#             status_code=400,
#             detail=f"❌ File '{file.filename}' already exists in uploads."
#         )

#     # ✅ Save original file permanently with original name
#     with open(file_path, "wb") as f:
#         f.write(await file.read())

#     # ✅ Use directly in DoclingLoader
#     loader = DoclingLoader(
#         file_path=[file_path],
#         export_type=ExportType.DOC_CHUNKS,
#         chunker=default_chunker,
#     )
#     docs = loader.load()

#     cleaned_chunks = []
#     buffer = None

#     for i, d in enumerate(docs):
#         text = d.page_content.strip()
#         meta = d.metadata or {}

#         dl_meta = meta.get("dl_meta", {})
#         headings = dl_meta.get("headings", [])
#         heading_key = ">".join(headings) if headings else None

#         # Extract first available page_no
#         page_no = None
#         if "doc_items" in dl_meta and len(dl_meta["doc_items"]) > 0:
#             prov = dl_meta["doc_items"][0].get("prov", [])
#             if prov and "page_no" in prov[0]:
#                 page_no = prov[0]["page_no"]

#         chunk_obj = {
#         "chunk_id": i + 1,
#         "content": text,
#         "metadata": {
#         "page": page_no,
#         "headings": ">".join(headings) if headings else None,   # ✅ flattened string
#         "section_title": heading_key,
#         "source": file_path,
#             },
#         }

#         # Merge consecutive same-heading chunks
#         if buffer:
#             buffer_norm = [h.strip().lower() for h in buffer["metadata"].get("headings", [])]
#             curr_norm = [h.strip().lower() for h in headings]
#             if buffer_norm == curr_norm and curr_norm:
#                 buffer["content"] += " " + text
#                 buffer["metadata"]["merged"] = True
#                 continue
#             else:
#                 cleaned_chunks.append(buffer)
#                 buffer = None

#         buffer = chunk_obj

#     if buffer:
#         cleaned_chunks.append(buffer)

#     return cleaned_chunks
