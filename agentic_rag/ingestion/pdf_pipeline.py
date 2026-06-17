"""PDF ingestion: parse, chunk hierarchically, embed into ChromaDB."""

import chromadb
import pdfplumber

from agentic_rag.config import CHROMA_DIR, PDF_DIR
from agentic_rag.llm import generate

PDF_COLLECTION = "pdf_chunks"


def _table_to_markdown(table: list[list[str]]) -> str:
    cleaned = []
    for row in table:
        cleaned.append([cell.replace("\n", " ").strip() if cell else "" for cell in row])
    header = cleaned[0]
    lines = ["| " + " | ".join(header) + " |"]
    lines.append("| " + " | ".join("---" for _ in header) + " |")
    for row in cleaned[1:]:
        while len(row) < len(header):
            row.append("")
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _extract_text(pdf_path) -> str:
    with pdfplumber.open(str(pdf_path)) as pdf:
        all_page_tables = []
        all_page_objs = []
        for page in pdf.pages:
            all_page_tables.append(page.extract_tables())
            all_page_objs.append(page.find_tables())

        margin = 100
        merged_tables: list[list[list[list[str]]]] = []
        for pi in range(len(all_page_tables)):
            page_merged = []
            page_h = pdf.pages[pi].height
            objs = all_page_objs[pi]

            for ti, table in enumerate(all_page_tables[pi]):
                if not table:
                    page_merged.append(table)
                    continue

                is_at_top = objs[ti].bbox[1] < margin
                prev_at_bottom = False
                if pi > 0 and all_page_objs[pi - 1]:
                    prev_page_h = pdf.pages[pi - 1].height
                    last_prev_bbox = all_page_objs[pi - 1][-1].bbox
                    prev_at_bottom = last_prev_bbox[3] > prev_page_h - margin

                if (
                    ti == 0
                    and is_at_top
                    and prev_at_bottom
                    and merged_tables
                    and merged_tables[-1]
                    and len(table[0]) == len(merged_tables[-1][-1][0])
                ):
                    prev_header = [(c or "").lower().strip() for c in merged_tables[-1][-1][0]]
                    curr_first = [(c or "").lower().strip() for c in table[0]]
                    if prev_header == curr_first:
                        merged_tables[-1][-1].extend(table[1:])
                    else:
                        merged_tables[-1][-1].extend(table)
                    page_merged.append([])
                else:
                    page_merged.append(table)

            merged_tables.append(page_merged)

        pages = []
        for pi, page in enumerate(pdf.pages):
            table_objs = all_page_objs[pi]
            tables = merged_tables[pi]

            filtered = page
            for tobj in table_objs:
                filtered = filtered.outside_bbox(tobj.bbox)
            text = filtered.extract_text() or ""

            words = page.extract_words(keep_blank_chars=True)
            insertions = []
            for ti, tobj in enumerate(table_objs):
                if ti >= len(tables) or not tables[ti] or len(tables[ti]) < 2:
                    continue
                table_top_y = tobj.bbox[1]
                lines_above = [w for w in words if w["bottom"] < table_top_y]
                if lines_above:
                    anchor = max(lines_above, key=lambda w: w["bottom"])["text"]
                    insertions.append((anchor, _table_to_markdown(tables[ti])))

            for anchor, md in reversed(insertions):
                idx = text.find(anchor)
                if idx != -1:
                    insert_at = idx + len(anchor)
                    text = text[:insert_at] + "\n" + md + "\n" + text[insert_at:]

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

        alpha_chars = [c for c in stripped if c.isalpha()]
        is_heading = (
            (stripped[0].isdigit() and ". " in stripped[:5])
            or (stripped.isupper() and len(alpha_chars) >= 5 and all(c.isalpha() or c.isspace() for c in stripped))
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

    sections = [s for s in sections if s["content"].strip()]

    if not sections:
        sections.append({
            "section_title": "Full Document",
            "content": text.strip(),
        })

    return sections


def _summarize_section(section_title: str, section_text: str) -> str:
    prompt = (
        f"Summarize this section in 2-3 sentences. Preserve key facts, numbers, and specifics.\n\n"
        f"Section: {section_title}\n\n{section_text}"
    )
    return generate(prompt)


def _summarize_document(source_name: str, section_summaries: list[str]) -> str:
    joined = "\n\n".join(section_summaries)
    prompt = (
        f"Summarize this document in 3-4 sentences. Capture the main purpose, key topics, and important specifics.\n\n"
        f"Document: {source_name}\n\nSection summaries:\n{joined}"
    )
    return generate(prompt)


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
        print(f"Processing {source_name}...")
        text = _extract_text(pdf_path)
        sections = _split_sections(text, source_name)

        section_summaries_for_doc = []

        for s_idx, section in enumerate(sections):
            section_id = f"{source_name}__s{s_idx}"

            section_summary = _summarize_section(section["section_title"], section["content"])
            section_summaries_for_doc.append(f"{section['section_title']}: {section_summary}")
            print(f"  Summarized section: {section['section_title']}")

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

        doc_summary = _summarize_document(source_name, section_summaries_for_doc)
        print(f"  Summarized document: {source_name}")

        all_ids.append(f"{source_name}__doc_summary")
        all_documents.append(doc_summary)
        all_metadatas.append({
            "source": source_name,
            "level": "document",
            "section": "Full Document",
            "chunk_index": 0,
        })

    collection.add(ids=all_ids, documents=all_documents, metadatas=all_metadatas)
    print(f"Ingested {len(pdf_files)} PDFs → {len(all_ids)} entries in ChromaDB")
    print(f"  Document summaries: {sum(1 for m in all_metadatas if m['level'] == 'document')}")
    print(f"  Section summaries: {sum(1 for m in all_metadatas if m['level'] == 'section')}")
    print(f"  Chunks: {sum(1 for m in all_metadatas if m['level'] == 'chunk')}")

    from agentic_rag.ingestion.image_pipeline import ingest_images
    ingest_images()


if __name__ == "__main__":
    ingest_pdfs()
