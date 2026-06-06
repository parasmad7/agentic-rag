"""PDF ingestion: parse, chunk hierarchically, embed into ChromaDB."""

import chromadb
from pypdf import PdfReader

from agentic_rag.config import CHROMA_DIR, PDF_DIR

PDF_COLLECTION = "pdf_chunks"


def _extract_text(pdf_path) -> str:
    reader = PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def _split_sections(text: str, source_name: str) -> list[dict]:
    lines = text.split("\n")
    sections = []
    current_section = None
    current_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            current_lines.append(line)
            continue

        is_heading = (
            (stripped[0].isdigit() and ". " in stripped[:5])
            or stripped.isupper()
            or (len(stripped) < 80 and not stripped.endswith(".") and not stripped.endswith(","))
        )

        if is_heading and current_lines and current_section:
            sections.append({
                "section_title": current_section,
                "content": "\n".join(current_lines).strip(),
            })
            current_lines = []

        if is_heading:
            current_section = stripped
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines and current_section:
        sections.append({
            "section_title": current_section,
            "content": "\n".join(current_lines).strip(),
        })

    if not sections:
        sections.append({
            "section_title": "Full Document",
            "content": text.strip(),
        })

    return sections


def _chunk_text(text: str, max_chars: int = 1000, overlap: int = 200) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        if end < len(text):
            break_point = text.rfind(". ", start, end)
            if break_point > start + max_chars // 2:
                end = break_point + 1
        chunks.append(text[start:end].strip())
        start = end - overlap
    return chunks


def ingest_pdfs():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(PDF_COLLECTION)
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=PDF_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        print("No PDFs found. Run generate_pdfs.py first.")
        return

    all_ids = []
    all_documents = []
    all_metadatas = []

    for pdf_path in pdf_files:
        source_name = pdf_path.name
        text = _extract_text(pdf_path)

        doc_summary = text[:500] + "..." if len(text) > 500 else text
        all_ids.append(f"{source_name}__doc_summary")
        all_documents.append(doc_summary)
        all_metadatas.append({
            "source": source_name,
            "level": "document",
            "section": "Full Document",
            "chunk_index": 0,
        })

        sections = _split_sections(text, source_name)

        for s_idx, section in enumerate(sections):
            section_id = f"{source_name}__s{s_idx}"
            section_summary = section["content"][:300]
            all_ids.append(f"{section_id}__summary")
            all_documents.append(f"[{source_name}] {section['section_title']}: {section_summary}")
            all_metadatas.append({
                "source": source_name,
                "level": "section",
                "section": section["section_title"],
                "chunk_index": 0,
            })

            chunks = _chunk_text(section["content"])
            for c_idx, chunk in enumerate(chunks):
                context_prefix = f"[Document: {source_name}] [Section: {section['section_title']}]\n"
                all_ids.append(f"{section_id}__c{c_idx}")
                all_documents.append(context_prefix + chunk)
                all_metadatas.append({
                    "source": source_name,
                    "level": "chunk",
                    "section": section["section_title"],
                    "chunk_index": c_idx,
                    "parent_section_id": f"{section_id}__summary",
                })

    collection.add(ids=all_ids, documents=all_documents, metadatas=all_metadatas)
    print(f"Ingested {len(pdf_files)} PDFs → {len(all_ids)} entries in ChromaDB")
    print(f"  Document summaries: {sum(1 for m in all_metadatas if m['level'] == 'document')}")
    print(f"  Section summaries: {sum(1 for m in all_metadatas if m['level'] == 'section')}")
    print(f"  Chunks: {sum(1 for m in all_metadatas if m['level'] == 'chunk')}")


if __name__ == "__main__":
    ingest_pdfs()
