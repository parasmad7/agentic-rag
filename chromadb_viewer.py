"""Streamlit viewer for the project's ChromaDB PDF vector store."""

import streamlit as st
import chromadb
from agentic_rag.config import CHROMA_DIR
from agentic_rag.ingestion.pdf_pipeline import PDF_COLLECTION

st.set_page_config(page_title="ChromaDB Viewer", layout="wide")
st.title("ChromaDB PDF Vector Store")

client = chromadb.PersistentClient(path=str(CHROMA_DIR))

try:
    collection = client.get_collection(PDF_COLLECTION)
except Exception:
    st.error(f"Collection '{PDF_COLLECTION}' not found. Run the PDF ingestion pipeline first.")
    st.stop()

all_data = collection.get(include=["documents", "metadatas"])
total = len(all_data["ids"])

sources = sorted({m["source"] for m in all_data["metadatas"]})
levels = {"document": [], "section": [], "chunk": []}

for i in range(total):
    entry = {
        "id": all_data["ids"][i],
        "document": all_data["documents"][i],
        "metadata": all_data["metadatas"][i],
    }
    levels[entry["metadata"]["level"]].append(entry)

# --- Sidebar ---
st.sidebar.header("Filters")
selected_source = st.sidebar.selectbox("PDF Source", ["All"] + sources)
selected_level = st.sidebar.selectbox("Level", ["All", "document", "section", "chunk"])

# --- Stats ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Entries", total)
col2.metric("Document Summaries", len(levels["document"]))
col3.metric("Section Summaries", len(levels["section"]))
col4.metric("Chunks", len(levels["chunk"]))

st.divider()

# --- Tree View ---
st.subheader("Hierarchical View")

for source in sources:
    if selected_source != "All" and source != selected_source:
        continue

    with st.expander(f"📄 {source}", expanded=(selected_source != "All")):
        doc_summaries = [e for e in levels["document"] if e["metadata"]["source"] == source]
        for doc in doc_summaries:
            if selected_level in ("All", "document"):
                st.markdown("**Document Summary**")
                st.text(doc["document"][:500])
                st.caption(f"`{doc['id']}`")

        sections = [e for e in levels["section"] if e["metadata"]["source"] == source]
        for sec in sections:
            section_name = sec["metadata"]["section"]
            if selected_level in ("All", "section"):
                st.markdown(f"**Section: {section_name}**")
                st.text(sec["document"][:400])
                st.caption(f"`{sec['id']}`")

            if selected_level in ("All", "chunk"):
                child_chunks = [
                    e for e in levels["chunk"]
                    if e["metadata"]["source"] == source
                    and e["metadata"]["section"] == section_name
                ]
                for chunk in sorted(child_chunks, key=lambda c: c["metadata"]["chunk_index"]):
                    st.markdown(f"  ↳ Chunk {chunk['metadata']['chunk_index']}")
                    st.code(chunk["document"], language=None)
                    parent_id = chunk["metadata"].get("parent_section_id", "—")
                    st.caption(f"`{chunk['id']}` → parent: `{parent_id}`")

st.divider()

# --- Search ---
st.subheader("Vector Search")
query = st.text_input("Search query", placeholder="e.g. What are the trainer certification requirements?")

if query:
    where_filter = {"level": "chunk"}
    if selected_source != "All":
        where_filter = {"$and": [{"level": "chunk"}, {"source": selected_source}]}

    results = collection.query(
        query_texts=[query],
        n_results=5,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    for i in range(len(results["ids"][0])):
        score = 1 - results["distances"][0][i]
        meta = results["metadatas"][0][i]
        doc = results["documents"][0][i]

        st.markdown(f"**Result {i+1}** — relevance: `{score:.3f}` | source: `{meta['source']}` | section: `{meta['section']}`")
        st.code(doc[:400], language=None)

        parent_id = meta.get("parent_section_id")
        if parent_id:
            parent = collection.get(ids=[parent_id], include=["documents"])
            if parent["documents"]:
                with st.expander("↑ Parent section context"):
                    st.text(parent["documents"][0][:400])
