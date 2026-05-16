from pathlib import Path

from sapling import index
from sapling.objects import hash_object
from sapling.plumbing import (
    checkout_branch,
    create_branch,
    get_branch_commit,
    get_current_branch,
    get_head_commit,
    list_branches,
    write_tree,
    commit_tree,
    update_ref,
)
from sapling.repository import Repository


def commit(repo: Repository, message: str) -> str:
    tree_sha = write_tree(repo)
    ref, parent = get_head_commit(repo)
    commit_sha = commit_tree(repo, tree_sha, parents=parent, message=message)
    update_ref(repo, ref or "refs/heads/master", commit_sha)
    return commit_sha


def test_branch_creation_and_listing(tmp_path: Path) -> None:
    repo = Repository(tmp_path)
    repo.init()

    (tmp_path / "file.txt").write_text("content\n", encoding="utf-8")
    index.add(repo, ["file.txt"])
    head_commit = commit(repo, "initial")

    create_branch(repo, "feature", head_commit)
    branches = list(list_branches(repo))
    assert "feature" in branches
    assert get_branch_commit(repo, "feature") == head_commit


def test_checkout_updates_worktree(tmp_path: Path) -> None:
    repo = Repository(tmp_path)
    repo.init()

    file_path = tmp_path / "file.txt"
    file_path.write_text("v1\n", encoding="utf-8")
    index.add(repo, ["file.txt"])
    first_commit = commit(repo, "first")

    create_branch(repo, "feature", first_commit)

    file_path.write_text("v2\n", encoding="utf-8")
    index.add(repo, ["file.txt"])
    commit(repo, "second")

    checkout_branch(repo, "feature")
    assert file_path.read_text(encoding="utf-8") == "v1\n"
    assert get_current_branch(repo) == "feature"

    idx = index.read(repo)
    expected_blob = hash_object(b"v1\n", write=False)
    assert idx.entries["file.txt"].oid == expected_blob
