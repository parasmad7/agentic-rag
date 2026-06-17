"""Image extraction from PDFs and CLIP-based indexing into ChromaDB."""

from pathlib import Path

import chromadb
import fitz
from PIL import Image

from agentic_rag.config import CHROMA_DIR, IMAGE_COLLECTION, IMAGE_DIR, PDF_DIR
from agentic_rag.ingestion.clip_embedder import embed_image

MIN_IMAGE_SIZE = 50


def _extract_images_from_pdf(pdf_path: Path) -> list[dict]:
    doc = fitz.open(str(pdf_path))
    images = []
    seen_xrefs = set()

    for page_num in range(len(doc)):
        page = doc[page_num]
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)

            base_image = doc.extract_image(xref)
            if not base_image or not base_image["image"]:
                continue

            width, height = base_image["width"], base_image["height"]
            if width < MIN_IMAGE_SIZE or height < MIN_IMAGE_SIZE:
                continue

            img_bytes = base_image["image"]
            ext = base_image["ext"]
            filename = f"{pdf_path.stem}_p{page_num}_x{xref}.{ext}"
            save_path = IMAGE_DIR / filename

            save_path.write_bytes(img_bytes)

            pil_image = Image.open(save_path).convert("RGB")

            images.append({
                "pil_image": pil_image,
                "page_num": page_num,
                "source": pdf_path.name,
                "image_path": filename,
                "width": width,
                "height": height,
            })

    doc.close()
    return images


def _embed_and_store_images(images: list[dict]):
    if not images:
        return

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(IMAGE_COLLECTION)
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=IMAGE_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

    ids = []
    embeddings = []
    documents = []
    metadatas = []

    for img in images:
        img_id = f"{img['source']}__{img['image_path']}"
        print(f"  Embedding: {img['image_path']} ({img['width']}x{img['height']})")
        embedding = embed_image(img["pil_image"])

        ids.append(img_id)
        embeddings.append(embedding)
        documents.append(f"Image from {img['source']} page {img['page_num'] + 1}")
        metadatas.append({
            "source": img["source"],
            "page_num": img["page_num"],
            "image_path": img["image_path"],
            "level": "image",
            "width": img["width"],
            "height": img["height"],
        })

    collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
    print(f"  Indexed {len(ids)} images in ChromaDB '{IMAGE_COLLECTION}'")


def ingest_images():
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        print("No PDFs found for image extraction.")
        return

    all_images = []
    for pdf_path in pdf_files:
        print(f"Extracting images from {pdf_path.name}...")
        images = _extract_images_from_pdf(pdf_path)
        print(f"  Found {len(images)} images")
        all_images.extend(images)

    if all_images:
        _embed_and_store_images(all_images)
    else:
        print("No images found in any PDF.")

    print(f"Image ingestion complete: {len(all_images)} total images")


if __name__ == "__main__":
    ingest_images()
