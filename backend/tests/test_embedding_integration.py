"""Opt-in real BGE snapshot and CPU inference acceptance test."""

import math
import os

import pytest

from backend.app.core.config import EmbeddingSettings, PROJECT_ROOT
from backend.app.services.embedding import EmbeddingClient

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.environ.get("RUN_LOCAL_EMBEDDING_INTEGRATION") != "1",
    reason="set RUN_LOCAL_EMBEDDING_INTEGRATION=1 for the local BGE test",
)
def test_real_bge_model_returns_normalized_512_dimension_vectors() -> None:
    """Download/cache the pinned model and run two Chinese passages on CPU."""
    settings = EmbeddingSettings(
        _env_file=None,
        cache_dir=PROJECT_ROOT / "data" / "models",
    )
    client = EmbeddingClient(settings)

    vectors = client.embed_documents(
        [
            "企业知识库需要保留来源页码。",
            "文档切分后可以生成本地向量。",
        ]
    )

    assert len(vectors) == 2
    assert all(len(vector) == 512 for vector in vectors)
    assert all(
        math.isclose(
            math.sqrt(sum(value * value for value in vector)),
            1.0,
            rel_tol=1e-4,
            abs_tol=1e-4,
        )
        for vector in vectors
    )
