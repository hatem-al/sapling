from pathlib import Path

from sapling import index
from sapling.objects import read_object
from sapling.plumbing import (
    checkout_branch,
    create_branch,
    get_branch_commit,
    get_head_commit,
    merge_branch,
    write_tree,
    commit_tree,
    update_ref,
)
from sapling.repository import Repository


def stage_and_commit(repo: Repository, filename: str, content: str, message: str) -> str:
    path = repo.worktree / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    index.add(repo, [filename])
    tree_sha = write_tree(repo)
    ref, parent = get_head_commit(repo)
    commit_sha = commit_tree(repo, tree_sha, parents=parent, message=message)
    update_ref(repo, ref or "refs/heads/master", commit_sha)
    return commit_sha


def test_fast_forward_merge(tmp_path: Path) -> None:
    repo = Repository(tmp_path)
    repo.init()

    base_commit = stage_and_commit(repo, "file.txt", "base\n", "base")
    create_branch(repo, "feature", base_commit)

    checkout_branch(repo, "feature")
    feature_commit = stage_and_commit(repo, "file.txt", "feature\n", "feature change")

    checkout_branch(repo, "master")
    result = merge_branch(repo, "feature")

    assert result["fast_forward"] is True
    assert result["commit"] == feature_commit
    assert (tmp_path / "file.txt").read_text(encoding="utf-8") == "feature\n"
    assert get_branch_commit(repo, "master") == feature_commit


def test_three_way_merge_creates_merge_commit(tmp_path: Path) -> None:
    repo = Repository(tmp_path)
    repo.init()

    base_commit = stage_and_commit(repo, "common.txt", "base\n", "base")
    create_branch(repo, "feature", base_commit)

    checkout_branch(repo, "feature")
    stage_and_commit(repo, "feature.txt", "feature\n", "feature work")

    checkout_branch(repo, "master")
    stage_and_commit(repo, "master.txt", "master\n", "master work")

    result = merge_branch(repo, "feature")

    assert result["fast_forward"] is False
    assert result["conflicts"] == []
    merge_commit = result["commit"]
    assert merge_commit is not None

    obj_type, data = read_object(merge_commit, repo=repo)
    assert obj_type == "commit"
    assert data.count(b"parent ") == 2
    assert (tmp_path / "feature.txt").exists()
    assert (tmp_path / "master.txt").exists()


def test_merge_conflict_writes_markers(tmp_path: Path) -> None:
    repo = Repository(tmp_path)
    repo.init()

    base_commit = stage_and_commit(repo, "conflict.txt", "base\n", "base")
    create_branch(repo, "feature", base_commit)

    checkout_branch(repo, "feature")
    stage_and_commit(repo, "conflict.txt", "theirs\n", "feature change")

    checkout_branch(repo, "master")
    master_commit = stage_and_commit(repo, "conflict.txt", "ours\n", "master change")

    result = merge_branch(repo, "feature")
    assert result["conflicts"] == ["conflict.txt"]
    assert result["commit"] is None

    file_text = (tmp_path / "conflict.txt").read_text(encoding="utf-8")
    assert "<<<<<<< HEAD" in file_text
    assert ">>>>>>> feature" in file_text

    _, head_commit = get_head_commit(repo)
    assert head_commit == master_commit
