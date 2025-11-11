from pathlib import Path

from sappling import index
from sappling.objects import read_object
from sappling.plumbing import commit_tree, get_head_commit, update_ref, write_tree
from sappling.repository import Repository


def read_tree_entries(repo: Repository, tree_sha: str) -> list[tuple[str, str]]:
    obj_type, payload = read_object(tree_sha, repo=repo)
    assert obj_type == "tree"
    entries = []
    i = 0
    while i < len(payload):
        end = payload.find(b"\x00", i)
        header = payload[i:end].decode()
        mode, name = header.split(" ", 1)
        sha = payload[end + 1 : end + 21].hex()
        entries.append((mode, name))
        i = end + 21
    return entries


def test_write_tree_handles_nested_directories(tmp_path: Path) -> None:
    repo = Repository(tmp_path)
    repo.init()
    (tmp_path / "dir").mkdir()

    (tmp_path / "file.txt").write_text("root\n", encoding="utf-8")
    (tmp_path / "dir" / "nested.txt").write_text("nested\n", encoding="utf-8")

    index.add(repo, ["file.txt", "dir/nested.txt"])

    tree_sha = write_tree(repo)
    entries = read_tree_entries(repo, tree_sha)
    assert ("100644", "file.txt") in entries
    assert ("40000", "dir") in entries


def test_commit_tree_updates_ref(tmp_path: Path) -> None:
    repo = Repository(tmp_path)
    repo.init()

    (tmp_path / "hello.txt").write_text("hello\n", encoding="utf-8")
    index.add(repo, ["hello.txt"])

    tree_sha = write_tree(repo)
    ref, parent = get_head_commit(repo)
    assert parent is None

    commit_sha = commit_tree(repo, tree_sha, parents=parent, message="initial commit")
    update_ref(repo, ref or "refs/heads/master", commit_sha)

    _, new_head = get_head_commit(repo)
    assert new_head == commit_sha

    obj_type, payload = read_object(commit_sha, repo=repo)
    assert obj_type == "commit"
    assert b"tree " + tree_sha.encode() in payload
    assert b"initial commit" in payload
