from pathlib import Path

from sappling import index
from sappling.plumbing import commit_tree, get_head_commit, update_ref, walk_commits, write_tree
from sappling.repository import Repository


def create_commit(repo: Repository, message: str) -> str:
    tree_sha = write_tree(repo)
    ref, parent = get_head_commit(repo)
    commit_sha = commit_tree(repo, tree_sha, parents=parent, message=message)
    update_ref(repo, ref or "refs/heads/master", commit_sha)
    return commit_sha


def test_walk_commits_returns_history(tmp_path: Path) -> None:
    repo = Repository(tmp_path)
    repo.init()

    (tmp_path / "file.txt").write_text("v1\n", encoding="utf-8")
    index.add(repo, ["file.txt"])
    first = create_commit(repo, "first")

    (tmp_path / "file.txt").write_text("v2\n", encoding="utf-8")
    index.add(repo, ["file.txt"])
    second = create_commit(repo, "second")

    commits = list(walk_commits(repo, second))
    assert [c["oid"] for c in commits] == [second, first]
    assert commits[0]["message"].startswith("second")
