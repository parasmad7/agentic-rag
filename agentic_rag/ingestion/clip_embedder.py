"""CLIP embedding for images and text. Lazy-loads model on first use."""

import open_clip
import torch
from PIL import Image

from agentic_rag.config import CLIP_MODEL_NAME, CLIP_PRETRAINED

_model = None
_preprocess = None
_tokenizer = None


def _load_model():
    global _model, _preprocess, _tokenizer
    if _model is not None:
        return
    _model, _, _preprocess = open_clip.create_model_and_transforms(
        CLIP_MODEL_NAME, pretrained=CLIP_PRETRAINED,
    )
    _tokenizer = open_clip.get_tokenizer(CLIP_MODEL_NAME)
    _model.eval()


def embed_image(pil_image: Image.Image) -> list[float]:
    _load_model()
    image_tensor = _preprocess(pil_image).unsqueeze(0)
    with torch.no_grad():
        features = _model.encode_image(image_tensor)
        features /= features.norm(dim=-1, keepdim=True)
    return features[0].tolist()


def embed_text(text: str) -> list[float]:
    _load_model()
    tokens = _tokenizer([text])
    with torch.no_grad():
        features = _model.encode_text(tokens)
        features /= features.norm(dim=-1, keepdim=True)
    return features[0].tolist()
