import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from sappling.plumbing import get_status
from sappling.repository import Repository

GIT_BIN = shutil.which("git")
SAP_CMD = [sys.executable, "-m", "sappling.cli"]

pytestmark = pytest.mark.skipif(GIT_BIN is None, reason="git executable is required")


def _run(cmd, cwd):
    result = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _git_status(repo: Path):
    staged = set(filter(None, _run([GIT_BIN, "diff", "--name-only", "--cached"], repo).splitlines()))
    modified = set(filter(None, _run([GIT_BIN, "diff", "--name-only"], repo).splitlines()))
    untracked = set(filter(None, _run([GIT_BIN, "ls-files", "--others", "--exclude-standard"], repo).splitlines()))
    return staged, modified, untracked


def _sap_status(repo: Path):
    status = get_status(Repository(repo))
    return set(status["staged"]), set(status["modified"]), set(status["untracked"])


def test_status_alignment(tmp_path: Path):
    git_repo = tmp_path / "git"
    sap_repo = tmp_path / "sap"
    git_repo.mkdir()
    sap_repo.mkdir()

    _run([GIT_BIN, "init", "-q", "."], git_repo)
    _run(SAP_CMD + ["init"], sap_repo)

    (git_repo / "foo.txt").write_text("hello\n", encoding="utf-8")
    (sap_repo / "foo.txt").write_text("hello\n", encoding="utf-8")

    _run([GIT_BIN, "add", "foo.txt"], git_repo)
    _run(SAP_CMD + ["add", "foo.txt"], sap_repo)

    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Parity",
        "GIT_AUTHOR_EMAIL": "parity@example.com",
        "GIT_COMMITTER_NAME": "Parity",
        "GIT_COMMITTER_EMAIL": "parity@example.com",
    }
    subprocess.run(
        [GIT_BIN, "commit", "-m", "init"],
        cwd=git_repo,
        check=True,
        capture_output=True,
        env=env,
        text=True,
    )
    subprocess.run(
        SAP_CMD + ["commit", "-m", "init"],
        cwd=sap_repo,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    (git_repo / "foo.txt").write_text("hello\nchange\n", encoding="utf-8")
    (sap_repo / "foo.txt").write_text("hello\nchange\n", encoding="utf-8")

    (git_repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    (sap_repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _run([GIT_BIN, "add", "tracked.txt"], git_repo)
    _run(SAP_CMD + ["add", "tracked.txt"], sap_repo)

    (git_repo / "untracked.txt").write_text("new\n", encoding="utf-8")
    (sap_repo / "untracked.txt").write_text("new\n", encoding="utf-8")

    git_status = _git_status(git_repo)
    sap_status = _sap_status(sap_repo)
    assert git_status == sap_status


def _normalized_diff(text: str):
    return [line for line in text.splitlines() if line.startswith(("+", "-"))]


def test_diff_alignment(tmp_path: Path):
    git_repo = tmp_path / "gitdiff"
    sap_repo = tmp_path / "sapdiff"
    git_repo.mkdir()
    sap_repo.mkdir()

    _run([GIT_BIN, "init", "-q", "."], git_repo)
    _run(SAP_CMD + ["init"], sap_repo)

    (git_repo / "file.txt").write_text("one\ntwo\n", encoding="utf-8")
    (sap_repo / "file.txt").write_text("one\ntwo\n", encoding="utf-8")

    _run([GIT_BIN, "add", "file.txt"], git_repo)
    _run(SAP_CMD + ["add", "file.txt"], sap_repo)

    subprocess.run(
        [GIT_BIN, "commit", "-m", "base"],
        cwd=git_repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        SAP_CMD + ["commit", "-m", "base"],
        cwd=sap_repo,
        check=True,
        capture_output=True,
        text=True,
    )

    (git_repo / "file.txt").write_text("one\nchanged\n", encoding="utf-8")
    (sap_repo / "file.txt").write_text("one\nchanged\n", encoding="utf-8")

    git_diff = _run([GIT_BIN, "-c", "color.diff=false", "diff", "file.txt"], git_repo)
    sap_diff = _run(SAP_CMD + ["diff", "file.txt"], sap_repo)

    assert _normalized_diff(git_diff) == _normalized_diff(sap_diff)
