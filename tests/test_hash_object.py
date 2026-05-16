import zlib

import pytest

from sapling.objects import ObjectMissingError, hash_object, read_object
from sapling.repository import Repository


def test_hash_object_writes_blob(tmp_path) -> None:
    repo = Repository(tmp_path)
    repo.init()

    payload = b"hello world\n"
    oid = hash_object(payload, repo=repo)

    obj_path = repo.git_dir / "objects" / oid[:2] / oid[2:]
    assert obj_path.exists()

    stored = zlib.decompress(obj_path.read_bytes())
    assert stored == f"blob {len(payload)}\0".encode() + payload


def test_read_object_round_trip(tmp_path) -> None:
    repo = Repository(tmp_path)
    repo.init()

    payload = b"some data"
    oid = hash_object(payload, repo=repo)

    obj_type, body = read_object(oid, repo=repo)
    assert obj_type == "blob"
    assert body == payload


def test_read_object_missing(tmp_path) -> None:
    repo = Repository(tmp_path)
    repo.init()

    with pytest.raises(ObjectMissingError):
        read_object("f" * 40, repo=repo)
