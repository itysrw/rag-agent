"""Offline Day 21 contracts for resolved Docker Compose configuration."""

from collections.abc import Callable
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]
LEGACY_POSTGRES_VOLUME = "rag-agent_postgres_data"
LEGACY_QDRANT_VOLUME = "rag-agent-qdrant-data"
ADMIN_TOKEN = "compose-test-token"


@pytest.fixture
def render_compose(tmp_path: Path) -> Callable[[str | None], dict[str, Any]]:
    """Resolve Compose without starting services or reading project dotenv values."""
    docker = shutil.which("docker")
    if docker is None:
        pytest.skip("Docker CLI is not installed")

    system_keys = {
        "APPDATA", "HOME", "LOCALAPPDATA", "PATH", "PATHEXT", "PROGRAMDATA",
        "PROGRAMFILES", "SYSTEMROOT", "TEMP", "TMP", "USERPROFILE", "WINDIR",
    }
    env = {key: value for key, value in os.environ.items() if key.upper() in system_keys}
    version = subprocess.run(
        [docker, "compose", "version"], env=env, capture_output=True, timeout=15,
    )
    if version.returncode != 0:
        pytest.skip("Docker Compose CLI is not available")
    env["POSTGRES_PASSWORD"] = "compose-test-password"
    env_file = tmp_path / "empty.env"
    env_file.touch()

    def render(token: str | None) -> dict[str, Any]:
        resolved_env = dict(env)
        if token is not None:
            resolved_env["ADMIN_TRACE_TOKEN"] = token
        result = subprocess.run(
            [docker, "compose", "--project-name", "rag-agent", "--env-file", str(env_file),
             "--file", str(ROOT / "docker-compose.yml"), "config", "--format", "json",
             "--no-env-resolution"],
            cwd=ROOT, env=resolved_env, capture_output=True, encoding="utf-8", timeout=30,
        )
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    return render


def _mounted_volume_name(config: dict[str, Any], service: str, target: str) -> str:
    (mount,) = [item for item in config["services"][service]["volumes"] if item["target"] == target]
    assert mount["type"] == "volume"
    return config["volumes"][mount["source"]]["name"]


def test_default_compose_does_not_pair_legacy_catalog_with_new_vector_volume(
    render_compose: Callable[[str | None], dict[str, Any]],
) -> None:
    config = render_compose(None)
    postgres = _mounted_volume_name(config, "postgres", "/var/lib/postgresql/data")
    qdrant = _mounted_volume_name(config, "qdrant", "/qdrant/storage")

    assert postgres != LEGACY_POSTGRES_VOLUME or qdrant == LEGACY_QDRANT_VOLUME, (
        f"The default Compose stack reuses the legacy catalog ({postgres}) "
        f"but mounts a different vector volume ({qdrant})."
    )


def test_compose_forwards_admin_trace_token_only_to_backend_when_configured(
    render_compose: Callable[[str | None], dict[str, Any]],
) -> None:
    enabled = render_compose(ADMIN_TOKEN)["services"]
    disabled = render_compose(None)["services"]

    assert (enabled["backend"].get("environment") or {}).get("ADMIN_TRACE_TOKEN") == ADMIN_TOKEN
    assert not (disabled["backend"].get("environment") or {}).get("ADMIN_TRACE_TOKEN")
    for service, settings in enabled.items():
        if service != "backend":
            assert "ADMIN_TRACE_TOKEN" not in (settings.get("environment") or {}), service
