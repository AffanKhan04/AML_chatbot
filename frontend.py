import streamlit as st
import requests , json

st.set_page_config(page_title="AML Regulation Chat", layout="wide")
st.title("💬 Ask...")

# initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_query_answered" not in st.session_state:
    st.session_state.last_query_answered = ""
if "requirements_response" not in st.session_state:
    st.session_state.requirements_response = None
if "show_requirements" not in st.session_state:
    st.session_state.show_requirements = False
if "actions_response" not in st.session_state:
    st.session_state.actions_response = None
if "show_actions" not in st.session_state:
    st.session_state.show_actions = False    
if "chat_id" not in st.session_state:
    st.session_state.chat_id=None
    
# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat Input
if prompt := st.chat_input("Ask a question about Regulations"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    # with st.chat_message("user"):
    st.markdown(
    f"""
    <div style='text-align: right;'>
    <div style='display: inline-block; background-color: #0059b3; color: white; padding: 10px 15px; border-radius: 15px; max-width: 70%; word-wrap: break-word;'>
    {prompt}
    </div>
    </div>
     """,
    unsafe_allow_html=True,
     )                                                                                 

    with st.chat_message("assistant"):
        with st.spinner("Searching our regulatory library..."):
            payload = {
                    "query": prompt,
                    "chat_id": st.session_state.chat_id   # or None for new chat
                    }
            response = requests.post(
                "http://localhost:8000/ask", json=payload
            )
            if response.status_code == 200:
                data = response.json()
                
                # ✅ Save the chat_id returned by backend if it's the first request
                if st.session_state.chat_id is None:
                    st.session_state.chat_id = data.get("chat_id")

                answer = data["response"]
                st.markdown(answer)
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer}
                )
                st.session_state.last_query_answered = answer
            else:
                st.error("❌ Failed to get response from backend.")
                
# --- Show Generate Requirements button if LLM response exists ---
if st.session_state.last_query_answered:
    if st.button("🧩 Generate Requirements"):
        with st.spinner("Extracting Requirements..."):
            response = requests.post("http://localhost:8000/requirements")
            if response.status_code == 200:
                st.session_state.requirements_response = response.json()["response"]
                st.session_state.show_requirements = True
            else:
                st.error("❌ Failed to extract requirements.")


#sidebar implementation
if st.session_state.show_requirements and st.session_state.requirements_response:
    with st.sidebar:
        st.subheader("📋 AML Requirements Extracted")
        pretty_json = json.dumps(st.session_state.requirements_response, indent=2)
        st.code(pretty_json, language="json")
        st.download_button("📥 Copy JSON", pretty_json, file_name="requirements.json")

        # --- Generate Actions button ---
        if st.button("⚡ Generate Actions", disabled=not st.session_state.requirements_response):
            with st.spinner("Generating Actions..."):
                response = requests.post("http://localhost:8000/actions")
                if response.status_code == 200:
                    st.session_state.actions_response = response.json()["response"]
                    st.session_state.show_actions = True
                else:
                    st.error("❌ Failed to generate actions.")

        # --- Show Actions if available ---
        if st.session_state.show_actions and st.session_state.actions_response:
            st.subheader("🚀 Actionable Tasks")
            pretty_actions = json.dumps(st.session_state.actions_response, indent=2)
            st.code(pretty_actions, language="json")
            st.download_button("📥 Copy Actions", pretty_actions, file_name="actions.json")

        # --- Close button ---
        if st.button("❌ Close", key="close-popup"):
            st.session_state.show_requirements = False
            st.session_state.requirements_response = None
            st.session_state.actions_response = None
            st.session_state.show_actions = False

# --- Divider for Upload ---
st.markdown("---")
st.subheader("📂 Upload Regulatory Documents")

# File uploader (accept multiple formats)
uploaded_file = st.file_uploader(
    "Upload a PDF, Word, or JSON file to add into the knowledge base:",
    type=["pdf", "docx", "json"],
)

if uploaded_file is not None:
    if st.button("🚀 Upload & Vectorize"):
        with st.spinner("Processing and vectorizing document..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
            response = requests.post("http://localhost:8000/upload_and_vectorize", files=files)

            if response.status_code == 200:
                data = response.json()
                st.success(data.get("detail", "✅ File uploaded successfully!"))
                st.info(f"📑 Chunks created: {data.get('chunks_added', 0)}")
            else:
                try:
                    st.error(response.json().get("detail", "❌ Upload failed."))
                except:
                    st.error("❌ Upload failed. Could not parse server response.")

# --- Divider ---
# st.markdown("---")
# st.subheader("📜 Chat History (From Backend)")

# # Fetch history from backend
# history_res = requests.get("http://localhost:8000/history")
# if history_res.status_code == 200:
#     history = history_res.json()
#     if history:
#         for chat in history:
#             with st.expander(f"{chat['question']} ({chat['timestamp']})"):
#                 st.write(f"**Q:** {chat['question']}")
#                 st.write(f"**A:** {chat['answer']}")
#                 if st.button(f"🗑 Delete", key=chat['id']):
#                     del_res = requests.delete(f"http://localhost:8000/history/{chat['id']}")
#                     if del_res.status_code == 200:
#                         st.success("Deleted successfully!")
#                         st.rerun()
#     else:
#         st.info("No history found.")
# else:
#     st.error("❌ Failed to fetch history from backend.")
