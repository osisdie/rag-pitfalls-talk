"""
坑 19 · Ingestion 的圖片陷阱   [Bucket 5: 基礎設施]

現象 Symptom:   6 個月後，系統回覆裡的圖片全部壞圖 — 外站改版、WAF 擋了爬蟲、
                短網址過期、CDN 換 host。
成因 Root cause: Ingestion 只存了 image URL，沒存圖片本體。URL 是別人家的資源。
解法 Solution:  Ingestion 階段下載圖片到本地 + S3 備援；payload 存三層 URL；前端有
                fallback chain（local → S3 → original）。
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any, Protocol

import requests

log = logging.getLogger(__name__)


class Blob(Protocol):
    def put(self, key: str, data: bytes) -> None: ...


# ❌ Anti-pattern / 反模式 ──────────────────────────────────────────
def ingest_with_url_only(doc: dict[str, Any]) -> dict[str, Any]:
    """
    Store external image URL. Every day the number of dead images grows; by the
    time a customer complains you've lost track of which images are live.
    """
    return {
        "text": doc["text"],
        "image_url": doc.get("image_url"),  # external — outside your control
    }


# ✅ Recommended / 建議寫法 ─────────────────────────────────────────
def materialize_images(
    doc: dict[str, Any],
    s3: Blob,
    local_dir: str,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    """
    Download every external image at ingestion time. Store locally (fast path)
    and on S3 (disaster recovery). Keep original URL for attribution.

    Frontend fallback chain: local_url → s3_url → original_url.
    """
    stored = []
    for url in doc.get("image_urls", []):
        try:
            response = requests.get(url, timeout=timeout_seconds)
            response.raise_for_status()
        except requests.RequestException as exc:
            log.warning("image_fetch_failed", extra={"url": url, "err": str(exc)})
            continue

        blob = response.content
        img_id = hashlib.sha256(blob).hexdigest()[:16]
        local_path = f"{local_dir}/{img_id}.bin"
        with open(local_path, "wb") as f:
            f.write(blob)
        s3.put(f"images/{img_id}", blob)

        stored.append({
            "id": img_id,
            "original_url": url,           # 保留歸屬 / keep for attribution
            "local_url": f"/img/{img_id}",
            "s3_url": f"s3://images/{img_id}",
        })
    doc["images"] = stored
    return doc
