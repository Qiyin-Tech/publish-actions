from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPT = (
    REPOSITORY / "actions" / "publish-docker" / "scripts" / "prepare-references"
)


def run_script(
    tmp_path: Path,
    *,
    owner: str = "Qiyin-Tech",
    package: str = "orchestra-backend",
    tags: str = "v1.2.3\ndev",
    push: str = "true",
) -> subprocess.CompletedProcess[str]:
    output = tmp_path / "github-output"
    env = os.environ.copy()
    env.update(
        {
            "GITHUB_OUTPUT": str(output),
            "OWNER": owner,
            "PACKAGE": package,
            "TAGS": tags,
            "PUSH": push,
        }
    )
    return subprocess.run(
        ["bash", str(SCRIPT)],
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def test_prepares_complete_references_from_package_and_plain_tags(tmp_path: Path) -> None:
    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    output = (tmp_path / "github-output").read_text(encoding="utf-8")
    assert "image=ghcr.io/qiyin-tech/orchestra-backend\n" in output
    assert "ghcr.io/qiyin-tech/orchestra-backend:v1.2.3\n" in output
    assert "ghcr.io/qiyin-tech/orchestra-backend:dev\n" in output


def test_rejects_full_image_reference_as_tag(tmp_path: Path) -> None:
    result = run_script(
        tmp_path,
        tags="ghcr.io/qiyin-tech/orchestra-backend:v1.2.3",
    )

    assert result.returncode == 1
    assert "Invalid Docker tag" in result.stderr


def test_rejects_duplicate_tags(tmp_path: Path) -> None:
    result = run_script(tmp_path, tags="dev\ndev")

    assert result.returncode == 1
    assert "Duplicate Docker tag" in result.stderr


def test_rejects_invalid_package_name(tmp_path: Path) -> None:
    result = run_script(tmp_path, package="Orchestra Backend")

    assert result.returncode == 1
    assert "Invalid GHCR package name" in result.stderr


def test_rejects_invalid_push_value(tmp_path: Path) -> None:
    result = run_script(tmp_path, push="yes")

    assert result.returncode == 1
    assert "push must be true or false" in result.stderr
