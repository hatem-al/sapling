from pathlib import Path

from sappling import index
from sappling.plumbing import generate_diff, get_status, write_tree, commit_tree, get_head_commit, update_ref
from sappling.repository import Repository


def commit(repo: Repository, message: str) -> str:
    tree = write_tree(repo)
    ref, parent = get_head_commit(repo)
    sha = commit_tree(repo, tree, parents=parent, message=message)
    update_ref(repo, ref or "refs/heads/master", sha)
    return sha


def test_status_reports_modified_staged_untracked(tmp_path: Path) -> None:
    repo = Repository(tmp_path)
    repo.init()

    file_path = tmp_path / "file.txt"
    file_path.write_text("v1\n", encoding="utf-8")
    index.add(repo, ["file.txt"])
    commit(repo, "initial")

    # modify working tree without staging
    file_path.write_text("v2\n", encoding="utf-8")
    (tmp_path / "new.txt").write_text("new\n", encoding="utf-8")

    status = get_status(repo)
    assert status["modified"] == ["file.txt"]
    assert status["staged"] == []
    assert "new.txt" in status["untracked"]

    # stage the change
    index.add(repo, ["file.txt"])
    status = get_status(repo)
    assert "file.txt" in status["staged"]
    assert "file.txt" not in status["modified"]


def test_generate_diff_shows_changes(tmp_path: Path) -> None:
    repo = Repository(tmp_path)
    repo.init()

    file_path = tmp_path / "file.txt"
    file_path.write_text("line1\nline2\n", encoding="utf-8")
    index.add(repo, ["file.txt"])
    commit(repo, "initial")

    file_path.write_text("line1\nchanged\n", encoding="utf-8")

    diff = generate_diff(repo)
    assert "-line2" in diff
    assert "+changed" in diff

    index.add(repo, ["file.txt"])
    staged_diff = generate_diff(repo, staged=True)
    assert "-line2" in staged_diff
