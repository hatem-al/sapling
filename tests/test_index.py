import json
from pathlib import Path

from sappling import index
from sappling.objects import hash_object
from sappling.repository import Repository


def test_index_add_stages_blob_and_metadata(tmp_path: Path) -> None:
    repo = Repository(tmp_path)
    repo.init()

    file_path = tmp_path / "hello.txt"
    file_path.write_text("hello world\n", encoding="utf-8")

    idx = index.read(repo)
    entry = idx.add("hello.txt")
    idx.write()

    on_disk = json.loads((repo.git_dir / "index").read_text(encoding="utf-8"))
    stored = on_disk["hello.txt"]

    assert stored["oid"] == entry.oid
    assert stored["size"] == len("hello world\n")
    assert stored["path"] == "hello.txt"

    obj_path = repo.git_dir / "objects" / entry.oid[:2] / entry.oid[2:]
    assert obj_path.exists()


def test_index_read_round_trip(tmp_path: Path) -> None:
    repo = Repository(tmp_path)
    repo.init()

    first = tmp_path / "a.txt"
    first.write_text("alpha", encoding="utf-8")
    second = tmp_path / "b.txt"
    second.write_text("beta", encoding="utf-8")

    index.add(repo, ["a.txt", "b.txt"])

    idx = index.read(repo)
    assert set(idx.entries.keys()) == {"a.txt", "b.txt"}

    expected_oid = hash_object(first.read_bytes(), repo=repo)
    assert idx.entries["a.txt"].oid == expected_oid
