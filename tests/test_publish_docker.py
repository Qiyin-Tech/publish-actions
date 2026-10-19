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
    ("branch", "tag", "ref_type", "ref_name", "version", "metadata_version"),
    [
        ("dev", "false", "branch", "dev", "v1.2.3", "v1.2.3"),
        ("test", "false", "branch", "test", "v1.2.3", "v1.2.3"),
        ("rc", "false", "branch", "rc/v1.2.3", "v1.2.3", "v1.2.3"),
        ("dev", "true", "tag", "v1.2.3", "v1.2.3", "v1.2.3"),
        (
            "dev",
            "false",
            "branch",
            "dev",
            '{"images":{"example_app":"v1.2.3","helper":"v4.5.6"}}',
            "v1.2.3",
        ),
        (
            "dev",
            "false",
            "branch",
            "dev",
            '{"pack":"候选版本 + build/43","images":{"helper":"nomad-packs validates this"}}',
            "候选版本 + build/43",
        ),
    ],
)
def test_update_pack_dispatch_contract(
    tmp_path: Path,
    branch: str,
    tag: str,
    ref_type: str,
    ref_name: str,
    version: str,
    metadata_version: str,
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
        "  echo '{\"workflow_run_id\":12345}'\n"
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
            "VERSION": version,
            "BRANCH": branch,
            "TAG": tag,
            "GIT_NAME": "Test",
            "GIT_EMAIL": "test@example.com",
            "GITHUB_REF_TYPE": ref_type,
            "GITHUB_REF_NAME": ref_name,
            "GITHUB_REPOSITORY": "Qiyin-Tech/example-app",
            "GITHUB_SHA": SHA,
            "GITHUB_REF": f"refs/{'tags' if ref_type == 'tag' else 'heads'}/{ref_name}",
            "GITHUB_RUN_ID": "3456",
            "GITHUB_RUN_ATTEMPT": "2",
            "RUNNER_TEMP": str(tmp_path),
            "EXPECTED_PACKS": "3",
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
    assert payload["inputs"]["metadata_version"] == metadata_version
    report = json.loads((tmp_path / "deploy-watch-example-app/report.json").read_text())
    assert report["source"]["id"] == 3456
    assert report["source"]["attempt"] == 2
    assert report["target"] == {"repo": "Qiyin-Tech/nomad-packs", "id": 12345, "workflow": "update-pack.yml"}
    assert report["outcome"] == "dispatched"
    assert report["expected_reports"] == 3
    if version.startswith("{"):
        assert json.loads(payload["inputs"]["docker_tag"]) == json.loads(version)
    else:
        assert payload["inputs"]["docker_tag"] == version


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
            "GITHUB_REF": "refs/heads/dev",
            "GITHUB_RUN_ID": "3456",
            "GITHUB_RUN_ATTEMPT": "1",
            "RUNNER_TEMP": str(tmp_path),
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
    report = json.loads((tmp_path / "deploy-watch-example-app/report.json").read_text())
    assert report["outcome"] == "superseded"
    assert "target" not in report
