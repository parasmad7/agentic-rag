"""Gemini Vision image descriptions with disk-based caching."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

from agentic_rag.config import IMAGE_DESCRIPTION_CACHE_DIR, IMAGE_DIR
from agentic_rag.llm import get_client
from agentic_rag.config import GEMINI_MODEL


def _cache_path(image_path: str) -> Path:
    key = hashlib.sha256(image_path.encode()).hexdigest()[:16]
    return IMAGE_DESCRIPTION_CACHE_DIR / f"{key}.json"


def describe_image(image_path: str, query_context: str = "") -> str:
    cache = _cache_path(image_path)
    if cache.exists():
        return json.loads(cache.read_text())["description"]

    full_path = IMAGE_DIR / image_path
    if not full_path.exists():
        return f"Image not found: {image_path}"

    pil_image = Image.open(full_path)

    prompt = "Describe this image in detail. Focus on data, charts, diagrams, and key visual information."
    if query_context:
        prompt += f" Context: {query_context}"

    client = get_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[prompt, pil_image],
    )

    description = response.text.strip()

    cache.write_text(json.dumps({
        "image_path": image_path,
        "description": description,
    }))

    return description


def describe_images_batch(
    image_paths: list[str], query_context: str = ""
) -> dict[str, str]:
    results = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(describe_image, path, query_context): path
            for path in image_paths
        }
        for future in futures:
            path = futures[future]
            results[path] = future.result()
    return results
