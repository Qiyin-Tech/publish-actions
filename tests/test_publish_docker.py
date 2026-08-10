from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


REPOSITORY = Path(__file__).resolve().parents[1]
DISPATCH_SCRIPT = (
    REPOSITORY / "actions" / "update-pack" / "scripts" / "dispatch-pack-update"
)
SHA = "0123456789abcdef0123456789abcdef01234567"


def test_actions_keep_protocol_boundaries_explicit() -> None:
    docker = (REPOSITORY / "actions" / "publish-docker" / "action.yml").read_text(
        encoding="utf-8"
    )
    update = (REPOSITORY / "actions" / "update-pack" / "action.yml").read_text(
        encoding="utf-8"
    )

    assert "rc_branch" not in docker
    assert "GITHUB_REF" not in docker
    assert "acr-sync" not in docker
    assert "package:" in docker
    assert "token:" in docker
    assert "architectures:" not in docker
    assert "platforms: linux/amd64" in docker
    assert "app_client_id" in update
    assert "app_private_key" in update
    assert "NOMAD_PACKS_APP_PRIVATE_KEY" not in update


@pytest.mark.parametrize(
    ("branch", "tag", "ref_type", "ref_name"),
    [
        ("dev", "false", "branch", "dev"),
        ("rc", "false", "branch", "release/v1.2.3"),
        ("dev", "true", "tag", "v1.2.3"),
    ],
)
def test_update_pack_dispatch_contract(
    tmp_path: Path, branch: str, tag: str, ref_type: str, ref_name: str
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    capture = tmp_path / "dispatch.json"
    fake_gh = bin_dir / "gh"
    fake_gh.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "if [[ \"$*\" == *'/git/ref/heads/'* ]]; then\n"
        "  printf '%s\\n' \"${GITHUB_SHA}\"\n"
        "else\n"
        "  cat > \"${CAPTURE_PATH}\"\n"
        "fi\n",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "CAPTURE_PATH": str(capture),
            "GH_TOKEN": "pack-token",
            "SOURCE_GH_TOKEN": "source-token",
            "PACK": "example-app",
            "VERSION": "v1.2.3",
            "BRANCH": branch,
            "TAG": tag,
            "GIT_NAME": "Test",
            "GIT_EMAIL": "test@example.com",
            "GITHUB_REF_TYPE": ref_type,
            "GITHUB_REF_NAME": ref_name,
            "GITHUB_REPOSITORY": "Qiyin-Tech/example-app",
            "GITHUB_SHA": SHA,
        }
    )

    result = subprocess.run(
        ["bash", str(DISPATCH_SCRIPT)],
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(capture.read_text(encoding="utf-8"))
    assert payload["inputs"]["branch"] == branch
    assert payload["inputs"]["tag"] == tag


def test_update_pack_skips_stale_branch_run(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    capture = tmp_path / "dispatch.json"
    fake_gh = bin_dir / "gh"
    fake_gh.write_text(
        "#!/usr/bin/env bash\n"
        "if [[ \"$*\" == *'/git/ref/heads/'* ]]; then\n"
        "  printf '%040d\\n' 1\n"
        "else\n"
        "  cat > \"${CAPTURE_PATH}\"\n"
        "fi\n",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "CAPTURE_PATH": str(capture),
            "GH_TOKEN": "pack-token",
            "SOURCE_GH_TOKEN": "source-token",
            "PACK": "example-app",
            "VERSION": "v1.2.3",
            "BRANCH": "dev",
            "TAG": "false",
            "GIT_NAME": "Test",
            "GIT_EMAIL": "test@example.com",
            "GITHUB_REF_TYPE": "branch",
            "GITHUB_REF_NAME": "dev",
            "GITHUB_REPOSITORY": "Qiyin-Tech/example-app",
            "GITHUB_SHA": SHA,
        }
    )

    result = subprocess.run(
        ["bash", str(DISPATCH_SCRIPT)],
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert not capture.exists()
    assert "Skipping stale dev build" in result.stdout
