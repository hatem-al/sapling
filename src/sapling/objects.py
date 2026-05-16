"""Content-addressable object storage compatible with Git's loose object format."""

from __future__ import annotations

import hashlib
import zlib
from pathlib import Path
from typing import Literal, Union

from .repository import Repository

ObjectType = Literal["blob", "tree", "commit", "tag"]


class ObjectMissingError(FileNotFoundError):
    """Raised when a requested object ID does not exist on disk."""


def hash_object(
    data: bytes,
    obj_type: ObjectType = "blob",
    *,
    repo: Union[Repository, Path, None] = None,
    write: bool = True,
) -> str:
    """Store data as a Git object and return its SHA-1 object ID.

    Git objects are `type + size + \0 + body` byte streams. The SHA-1 digest of
    that canonical representation becomes both the object's ID and its storage
    path under `.git/objects/aa/bb…`. Loose objects are compressed with zlib to
    match Git's on-disk format exactly.
    """

    header = f"{obj_type} {len(data)}\0".encode()
    store = header + data
    oid = hashlib.sha1(store).hexdigest()

    if write:
        git_dir = _coerce_git_dir(repo)
        if git_dir is None:
            raise ValueError("repo must be provided when write=True")
        _write_object(git_dir, oid, store)

    return oid


def read_object(
    oid: str,
    *,
    repo: Union[Repository, Path, None],
) -> tuple[ObjectType, bytes]:
    """Load an object from `.git/objects/` and return its type + payload."""

    git_dir = _coerce_git_dir(repo)
    if git_dir is None:
        raise ValueError("repo must be provided when reading objects")

    obj_path = git_dir / "objects" / oid[:2] / oid[2:]
    if not obj_path.exists():
        raise ObjectMissingError(f"Object {oid} is missing under {obj_path}")

    compressed = obj_path.read_bytes()
    try:
        raw = zlib.decompress(compressed)
    except zlib.error as exc:  # pragma: no cover - signals on-disk corruption
        raise ValueError(f"Object {oid} is not valid zlib data") from exc

    header, _, body = raw.partition(b"\x00")
    if not _:
        raise ValueError(f"Object {oid} has no header separator")

    type_bytes, _, size_bytes = header.partition(b" ")
    if not _:
        raise ValueError(f"Object {oid} header is malformed: {header!r}")

    obj_type = type_bytes.decode()
    size = int(size_bytes)
    if len(body) != size:
        raise ValueError(f"Object {oid} declared size {size} but stored {len(body)} bytes")

    return obj_type, body


def _coerce_git_dir(repo: Union[Repository, Path, None]) -> Path | None:
    if repo is None:
        return None
    if isinstance(repo, Repository):
        return repo.git_dir
    return Path(repo)


def _write_object(git_dir: Path, oid: str, payload: bytes) -> None:
    obj_dir = git_dir / "objects" / oid[:2]
    obj_path = obj_dir / oid[2:]
    obj_dir.mkdir(parents=True, exist_ok=True)

    if obj_path.exists():  # Object content-addressed; skip rewriting to avoid races
        return

    compressed = zlib.compress(payload)
    obj_path.write_bytes(compressed)
