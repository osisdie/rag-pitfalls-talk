"""Vertex AI Gemini wrapper using the unified google-genai SDK.

Auth chain (in order):
    1. VM metadata service (production, preferred — no key file)
    2. ADC (GOOGLE_APPLICATION_CREDENTIALS env var pointing at SA json)
    3. Explicit SA file (google_application_credentials setting)

The demo's `LLMConfig` is a server-held singleton that the frontend
mutates via `POST /api/llm`. A single request can still override via
kwargs (used by the intent router in pit_09, where `gemini-2.5-flash-lite`
is cheaper than main).
"""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

from google import genai
from google.genai import types

from app.config import get_settings
from app.models.schemas import LLMConfig

log = logging.getLogger(__name__)

_client: genai.Client | None = None
_config: LLMConfig = LLMConfig()


def get_client() -> genai.Client:
    global _client
    if _client is None:
        s = get_settings()
        _client = genai.Client(
            vertexai=True,
            project=s.vertex_project_id,
            location=s.resolve_vertex_location(),
        )
    return _client


def get_config() -> LLMConfig:
    return _config


def set_config(cfg: LLMConfig) -> LLMConfig:
    global _config
    # Web Search grounding only on non-lite
    if cfg.web_search and cfg.model == "gemini-2.5-flash-lite":
        cfg = cfg.model_copy(update={"web_search": False})
    _config = cfg
    return _config


def _build_tools(cfg: LLMConfig) -> list[types.Tool] | None:
    tools: list[types.Tool] = []
    if cfg.web_search and cfg.model != "gemini-2.5-flash-lite":
        tools.append(types.Tool(google_search=types.GoogleSearch()))
    return tools or None


async def generate_stream(
    prompt: str,
    *,
    model: str | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    web_search: bool | None = None,
    system: str | None = None,
) -> AsyncIterator[str]:
    """Yield token chunks from Gemini via Vertex AI streaming."""
    cfg = _config
    effective = LLMConfig(
        model=model or cfg.model,  # type: ignore[arg-type]
        temperature=cfg.temperature if temperature is None else temperature,
        top_p=cfg.top_p if top_p is None else top_p,
        web_search=cfg.web_search if web_search is None else web_search,
    )
    gen_config = types.GenerateContentConfig(
        temperature=effective.temperature,
        top_p=effective.top_p,
        system_instruction=system,
        tools=_build_tools(effective),
    )

    client = get_client()
    loop = asyncio.get_running_loop()

    def _start_stream():
        return client.models.generate_content_stream(
            model=effective.model,
            contents=prompt,
            config=gen_config,
        )

    try:
        stream = await loop.run_in_executor(None, _start_stream)
    except Exception as exc:
        log.exception("Vertex start_stream failed: %s", exc)
        yield f"[LLM error: {exc}]"
        return

    try:
        while True:
            chunk = await loop.run_in_executor(None, next, stream, None)
            if chunk is None:
                break
            text = getattr(chunk, "text", None)
            if text:
                yield text
    except Exception as exc:
        log.exception("Vertex stream iteration failed: %s", exc)
        yield f"[LLM error: {exc}]"


async def generate(
    prompt: str,
    *,
    model: str | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    web_search: bool | None = None,
    system: str | None = None,
) -> str:
    chunks: list[str] = []
    async for token in generate_stream(
        prompt,
        model=model,
        temperature=temperature,
        top_p=top_p,
        web_search=web_search,
        system=system,
    ):
        chunks.append(token)
    return "".join(chunks)
