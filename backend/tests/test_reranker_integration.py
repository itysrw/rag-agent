"""Opt-in pinned CPU CrossEncoder acceptance, without database or paid APIs."""

import json
import math
import os
from dataclasses import replace

import pytest

from backend.app.core.config import RerankerSettings
from backend.app.services.reranker import RerankerService
from backend.tests.test_reranker import candidates

pytestmark = [pytest.mark.integration, pytest.mark.skipif(
    os.environ.get("RUN_RERANKER_INTEGRATION") != "1",
    reason="enable the real pinned local reranker",
)]


def test_real_pinned_cpu_model_scores_pairs_and_records_truncation() -> None:
    items = candidates(3)
    items[0] = replace(items[0], content="VPN 故障请联系网络组，服务分机是 6203。")
    items[1] = replace(items[1], content="报销票据需要在每月二十五日前交财务组。")
    items[2] = replace(items[2], content="访客进入办公区需要先登记。" * 250)
    reranker = RerankerService(RerankerSettings(_env_file=None))
    cold = reranker.rerank("VPN 故障找谁处理？", items)
    warm = reranker.rerank("VPN 故障找谁处理？", items)
    assert cold.results[0].chunk_id == items[0].chunk_id
    assert cold.truncated_candidate_count == 1
    assert all(math.isfinite(item.score) for item in cold.results)
    assert [item.chunk_id for item in cold.results] == [item.chunk_id for item in warm.results]
    assert warm.model_load_seconds == 0
    print("DAY12_RERANKER_MODEL_RESULT " + json.dumps({
        "revision": reranker.settings.model_revision,
        "cold_model_load_seconds": cold.model_load_seconds,
        "cold_inference_seconds": cold.inference_seconds,
        "warm_inference_seconds": warm.inference_seconds,
        "truncated_candidate_count": cold.truncated_candidate_count,
    }))
