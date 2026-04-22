"""
坑 14 · AI Vibe Coding 的反模式 — 不要為了一題改 hybrid 權重   [Bucket 4: 護欄的拿捏]

現象 Symptom:   為了修 bug #1234 把 HYBRID_ALPHA 從 0.7 改成 0.9；明天發現 bug #1240 是
                昨天被你改壞的。參數變成 magic-number 泥淖。
成因 Root cause: 無量化的「變好 / 變壞」判準。每次 tuning 依賴感覺 + 2-3 題手測。
解法 Solution:  Golden-set regression gate — 任何參數變動必須過 CI 閘門才能合併。
"""
from __future__ import annotations

import logging
import sys
from typing import Protocol

from ._common import Query

log = logging.getLogger(__name__)


class BenchmarkRunner(Protocol):
    def __call__(self, golden_set: list[Query], params: dict) -> dict[str, float]: ...


# ❌ Anti-pattern / 反模式 ──────────────────────────────────────────
# 實戰中很常見、很致命 — paste here as a teaching specimen:

HYBRID_ALPHA = 0.9   # TODO: 那題搜不到調了一下
RRF_K = 40           # 保額查詢壞了，改小看看？
# ... 3 個月後沒人知道為什麼這些常數是現在這個值


# ✅ Recommended / 建議寫法 ─────────────────────────────────────────
METRICS_TO_GATE = ("top1_accuracy", "faithfulness", "context_precision")


def regression_gate(
    golden_set: list[Query],
    new_params: dict,
    baseline: dict[str, float],
    run_benchmark: BenchmarkRunner,
    tolerance: float = 0.03,          # 任何指標掉 >3% 就擋 / any >3% drop fails
) -> bool:
    """
    Run the benchmark with the candidate params. Fail if any watched metric
    regresses beyond tolerance against the baseline.

    Wire this into CI: no merge without a green gate. The point isn't perfect
    metrics — it's *visibility* on what each change costs.
    """
    current = run_benchmark(golden_set, new_params)
    for metric in METRICS_TO_GATE:
        if current[metric] < baseline[metric] - tolerance:
            log.error(
                "regression",
                extra={
                    "metric": metric,
                    "baseline": baseline[metric],
                    "candidate": current[metric],
                },
            )
            return False
    return True


if __name__ == "__main__":
    # CI entrypoint — exit 1 to block the merge.
    sys.exit(0)  # wired to actual benchmark in your repo
