from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPT = REPOSITORY / "actions" / "publish-docker" / "scripts" / "prepare-metadata"
DISPATCH_SCRIPT = (
    REPOSITORY / "actions" / "update-pack" / "scripts" / "dispatch-pack-update"
)
CHECK_SCRIPT = (
    REPOSITORY / "actions" / "publish-docker" / "scripts" / "check-current-ref"
)
SHA = "0123456789abcdef0123456789abcdef01234567"


def test_publish_docker_keeps_acr_and_pack_updates_outside() -> None:
    action = (REPOSITORY / "actions" / "publish-docker" / "action.yml").read_text(
        encoding="utf-8"
    )
    workflow = (
        REPOSITORY / ".github" / "workflows" / "publish-docker.yml"
    ).read_text(encoding="utf-8")

    assert "acr-sync" not in action
    assert "actions/update-pack" not in action
    assert "Qiyin-Tech/acr-sync@v2" in workflow
    assert "uses: $/actions/update-pack" in workflow


def run_metadata(
    tmp_path: Path,
    *,
    event: str,
    ref: str,
    ref_name: str,
    ref_type: str = "branch",
    rc_branch: str = "",
    cache_from_tag: str = "buildcache",
    cache_export: str = "registry",
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    output = tmp_path / "github-output"
    env = os.environ.copy()
    env.update(
        {
            "GITHUB_EVENT_NAME": event,
            "GITHUB_OUTPUT": str(output),
            "GITHUB_REF": ref,
            "GITHUB_REF_NAME": ref_name,
            "GITHUB_REF_TYPE": ref_type,
            "GITHUB_REPOSITORY": "Qiyin-Tech/Example-App",
            "GITHUB_SHA": SHA,
            "RC_BRANCH": rc_branch,
            "CACHE_FROM_TAG": cache_from_tag,
            "CACHE_EXPORT": cache_export,
        }
    )
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=cwd or tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def test_selected_release_branch_prepares_rc_tags(tmp_path: Path) -> None:
    result = run_metadata(
        tmp_path,
        event="push",
        ref="refs/heads/release/v1.2.3",
        ref_name="release/v1.2.3",
        rc_branch="release/v1.2.3",
    )

    assert result.returncode == 0, result.stderr
    output = (tmp_path / "github-output").read_text(encoding="utf-8")
    assert "kind=rc\n" in output
    assert f"image_tag=rc-v1.2.3-{SHA}\n" in output
    assert "moving_tag=rc\n" in output
    assert "ghcr.io/qiyin-tech/example-app:rc\n" not in output
    assert f"ghcr.io/qiyin-tech/example-app:rc-v1.2.3-{SHA}\n" in output
    assert "cache_to=type=registry,ref=ghcr.io/qiyin-tech/example-app:buildcache,mode=max\n" in output


def test_non_selected_release_branch_is_rejected(tmp_path: Path) -> None:
    result = run_metadata(
        tmp_path,
        event="push",
        ref="refs/heads/release/v1.2.2",
        ref_name="release/v1.2.2",
        rc_branch="release/v1.2.3",
    )

    assert result.returncode == 1
    assert "is not the configured rc_branch" in result.stderr


def test_prerelease_tag_cannot_bypass_rc_branch(tmp_path: Path) -> None:
    result = run_metadata(
        tmp_path,
        event="push",
        ref="refs/tags/v1.2.3-rc1",
        ref_name="v1.2.3-rc1",
        ref_type="tag",
    )

    assert result.returncode == 1
    assert "unsupported release tag" in result.stderr


def test_dev_uses_nearest_formal_tag(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repository,
        check=True,
    )
    (repository / "README.md").write_text("test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=repository, check=True)
    subprocess.run(["git", "tag", "v1.1.0"], cwd=repository, check=True)

    result = run_metadata(
        tmp_path,
        event="push",
        ref="refs/heads/dev",
        ref_name="dev",
        cache_from_tag="dev",
        cache_export="inline",
        cwd=repository,
    )

    assert result.returncode == 0, result.stderr
    output = (tmp_path / "github-output").read_text(encoding="utf-8")
    assert "kind=dev\n" in output
    assert f"image_tag=dev-v1.1.0-{SHA}\n" in output
    assert "cache_from=type=registry,ref=ghcr.io/qiyin-tech/example-app:dev\n" in output
    assert "cache_to=type=inline\n" in output


def test_dev_ignores_prerelease_tags_when_finding_base_version(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repository,
        check=True,
    )
    (repository / "README.md").write_text("test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=repository, check=True)
    subprocess.run(["git", "tag", "v1.1.0"], cwd=repository, check=True)
    subprocess.run(["git", "tag", "v1.2.0-rc1"], cwd=repository, check=True)

    result = run_metadata(
        tmp_path,
        event="push",
        ref="refs/heads/dev",
        ref_name="dev",
        cwd=repository,
    )

    assert result.returncode == 0, result.stderr
    output = (tmp_path / "github-output").read_text(encoding="utf-8")
    assert f"image_tag=dev-v1.1.0-{SHA}\n" in output


def test_manual_build_does_not_export_cache(tmp_path: Path) -> None:
    result = run_metadata(
        tmp_path,
        event="workflow_dispatch",
        ref="refs/heads/dev",
        ref_name="dev",
    )

    assert result.returncode == 0, result.stderr
    output = (tmp_path / "github-output").read_text(encoding="utf-8")
    assert "kind=manual\n" in output
    assert f"image_tag=manual-{SHA}\n" in output
    assert "cache_to=\n" in output


@pytest.mark.parametrize(
    ("mode", "channel", "guard_ref", "expected_create_tag"),
    [
        ("moving", "dev", "dev", "false"),
        ("moving", "rc", "release/v1.2.3", "false"),
        ("release", "dev", "", "true"),
    ],
)
def test_update_pack_dispatch_contract(
    tmp_path: Path,
    mode: str,
    channel: str,
    guard_ref: str,
    expected_create_tag: str,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    capture = tmp_path / "dispatch.json"
    fake_gh = bin_dir / "gh"
    fake_gh.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "if [[ \"$*\" == *'/git/ref/heads/'* ]]; then\n"
        "  printf '%s\\n' \"${EXPECTED_SHA}\"\n"
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
            "EXPECTED_SHA": SHA,
            "GH_TOKEN": "pack-token",
            "SOURCE_GH_TOKEN": "source-token",
            "PACK": "example-app",
            "VERSION": f"test-v1.2.3-{SHA}",
            "CHANNEL": channel,
            "MODE": mode,
            "GUARD_REF": guard_ref,
            "GIT_NAME": "Test",
            "GIT_EMAIL": "test@example.com",
            "GITHUB_REPOSITORY": "Qiyin-Tech/example-app",
            "GITHUB_SHA": SHA,
            "GITHUB_OUTPUT": str(tmp_path / "github-output"),
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
    assert payload["ref"] == "main"
    assert payload["inputs"]["channel"] == channel
    assert payload["inputs"]["create_tag"] == expected_create_tag
    assert payload["inputs"]["docker_tag"] == f"test-v1.2.3-{SHA}"


@pytest.mark.parametrize(("latest_sha", "expected"), [(SHA, "true"), ("1" * 40, "false")])
def test_check_current_ref(tmp_path: Path, latest_sha: str, expected: str) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_gh = bin_dir / "gh"
    fake_gh.write_text(
        "#!/usr/bin/env bash\nprintf '%s\\n' \"${LATEST_SHA}\"\n",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)
    output = tmp_path / "github-output"
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "LATEST_SHA": latest_sha,
            "GH_TOKEN": "source-token",
            "REF": "release/v1.2.3",
            "GITHUB_REPOSITORY": "Qiyin-Tech/example-app",
            "GITHUB_SHA": SHA,
            "GITHUB_OUTPUT": str(output),
        }
    )

    result = subprocess.run(
        ["bash", str(CHECK_SCRIPT)],
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert f"current={expected}\n" in output.read_text(encoding="utf-8")


def test_update_pack_skips_stale_guarded_build(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    capture = tmp_path / "dispatch.json"
    fake_gh = bin_dir / "gh"
    fake_gh.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "if [[ \"$*\" == *'/git/ref/heads/'* ]]; then\n"
        "  printf '%s\\n' '1111111111111111111111111111111111111111'\n"
        "else\n"
        "  cat > \"${CAPTURE_PATH}\"\n"
        "fi\n",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)
    output = tmp_path / "github-output"
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "CAPTURE_PATH": str(capture),
            "GH_TOKEN": "pack-token",
            "SOURCE_GH_TOKEN": "source-token",
            "PACK": "example-app",
            "VERSION": f"rc-v1.2.3-{SHA}",
            "CHANNEL": "rc",
            "MODE": "moving",
            "GUARD_REF": "release/v1.2.3",
            "GIT_NAME": "Test",
            "GIT_EMAIL": "test@example.com",
            "GITHUB_REPOSITORY": "Qiyin-Tech/example-app",
            "GITHUB_SHA": SHA,
            "GITHUB_OUTPUT": str(output),
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
    assert "dispatched=false\n" in output.read_text(encoding="utf-8")
