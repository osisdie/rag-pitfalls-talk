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
_START_TIMEOUT_S = 5.0
_CHUNK_TIMEOUT_S = 30.0
_RETRY_ATTEMPTS = 2  # first try + 1 retry


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

    def _start_stream(selected_model: str):
        return client.models.generate_content_stream(
            model=selected_model,
            contents=prompt,
            config=gen_config,
        )

    def _is_quota_error(exc: Exception) -> bool:
        msg = str(exc)
        return "429" in msg or "RESOURCE_EXHAUSTED" in msg

    candidate_models = [effective.model]
    if effective.model == "gemini-2.5-flash-lite":
        candidate_models.append("gemini-2.5-flash")

    last_exc: Exception | None = None
    for midx, selected_model in enumerate(candidate_models):
        for attempt in range(1, _RETRY_ATTEMPTS + 1):
            stream = None
            emitted_any = False
            try:
                stream = await asyncio.wait_for(
                    loop.run_in_executor(None, _start_stream, selected_model),
                    timeout=_START_TIMEOUT_S,
                )
                while True:
                    chunk = await asyncio.wait_for(
                        loop.run_in_executor(None, next, stream, None),
                        timeout=_CHUNK_TIMEOUT_S,
                    )
                    if chunk is None:
                        return
                    text = getattr(chunk, "text", None)
                    if text:
                        emitted_any = True
                        yield text
            except Exception as exc:
                last_exc = exc
                is_last_attempt = attempt >= _RETRY_ATTEMPTS
                can_try_next_model = midx < len(candidate_models) - 1

                if isinstance(exc, asyncio.TimeoutError):
                    log.warning(
                        "Vertex stream timeout model=%s attempt=%d/%d",
                        selected_model,
                        attempt,
                        _RETRY_ATTEMPTS,
                    )
                else:
                    log.warning(
                        "Vertex stream failed model=%s attempt=%d/%d: %s",
                        selected_model,
                        attempt,
                        _RETRY_ATTEMPTS,
                        exc,
                    )

                # Retry only makes sense before we stream any token to caller.
                if (not emitted_any) and (not is_last_attempt):
                    await asyncio.sleep(0.5)
                    continue

                # If on lite and quota-limited, escalate to flash.
                if can_try_next_model and _is_quota_error(exc):
                    log.warning(
                        "Quota on %s, falling back to %s",
                        selected_model,
                        candidate_models[midx + 1],
                    )
                    break

                yield f"[LLM error: {exc}]"
                return

    # Exhausted all retries and fallbacks.
    yield f"[LLM error: {last_exc or 'unknown'}]"


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
