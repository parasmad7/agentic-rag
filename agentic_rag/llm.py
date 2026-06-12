"""Shared Gemini client using service account credentials via Vertex AI."""

import os

from google import genai
from google.genai.types import GenerateContentConfig, ThinkingConfig
from google.oauth2 import service_account

from agentic_rag.config import (
    GCP_LOCATION,
    GCP_PROJECT,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    SERVICE_ACCOUNT_KEY,
)

_client = None


def get_client() -> genai.Client:
    global _client
    if _client is not None:
        return _client

    if GEMINI_API_KEY:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    elif SERVICE_ACCOUNT_KEY.exists():
        credentials = service_account.Credentials.from_service_account_file(
            str(SERVICE_ACCOUNT_KEY),
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(SERVICE_ACCOUNT_KEY)
        _client = genai.Client(
            vertexai=True,
            project=GCP_PROJECT,
            location=GCP_LOCATION,
            credentials=credentials,
        )
    else:
        raise RuntimeError(
            "No Gemini credentials found. Set GEMINI_API_KEY env var "
            "or place a service account key in the project root."
        )

    return _client


def generate(prompt: str) -> str:
    client = get_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=GenerateContentConfig(
            thinking_config=ThinkingConfig(thinking_budget=0),
        ),
    )
    return response.text.strip()


def generate_stream(prompt: str):
    client = get_client()
    for chunk in client.models.generate_content_stream(
        model=GEMINI_MODEL,
        contents=prompt,
        config=GenerateContentConfig(
            thinking_config=ThinkingConfig(thinking_budget=0),
        ),
    ):
        if chunk.text:
            yield chunk.text
