"""GET/POST /api/llm — runtime knobs (model, temperature, top_p, web_search).

Server-held singleton (not per-session) because the demo is single-speaker.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.core import llm
from app.models.schemas import LLMConfig

router = APIRouter()


@router.get("/llm", response_model=LLMConfig)
async def get_llm_config() -> LLMConfig:
    return llm.get_config()


@router.post("/llm", response_model=LLMConfig)
async def set_llm_config(cfg: LLMConfig) -> LLMConfig:
    return llm.set_config(cfg)
