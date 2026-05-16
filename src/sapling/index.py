"""Simplified staging area (index) built on top of Git's object store.

The real Git index is a binary format optimized for speed. For pedagogy we use a
JSON file at `.git/index` that captures the same essential metadata: file mode,
modification time, size, and the blob OID. This keeps the storage model obvious
while we focus on behavior parity with Git's porcelain.
"""

from __future__ import annotations

import json
import os
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable

from .objects import hash_object
from .repository import Repository


@dataclass
class IndexEntry:
    path: str
    mode: int
    mtime: float
    size: int
    oid: str


class Index:
    """In-memory representation of the staging area."""

    def __init__(self, repo: Repository, entries: Dict[str, IndexEntry] | None = None) -> None:
        self.repo = repo
        self.entries: Dict[str, IndexEntry] = entries or {}

    @property
    def path(self) -> Path:
        return self.repo.git_dir / "index"

    def add(self, file_path: Path | str) -> IndexEntry:
        """Stage a file by hashing its content and recording metadata."""

        file_path = Path(file_path)
        worktree = self.repo.worktree
        abs_path = (worktree / file_path).resolve() if not file_path.is_absolute() else file_path

        if not abs_path.exists():
            raise FileNotFoundError(f"Cannot add missing path {abs_path}")

        rel_path = os.path.relpath(abs_path, worktree)

        data = abs_path.read_bytes()
        oid = hash_object(data, repo=self.repo)

        stat_result = abs_path.stat()
        mode = stat.S_IFREG | stat.S_IMODE(stat_result.st_mode)
        entry = IndexEntry(
            path=rel_path,
            mode=mode,
            mtime=stat_result.st_mtime,
            size=stat_result.st_size,
            oid=oid,
        )
        self.entries[rel_path] = entry
        return entry

    def to_json(self) -> str:
        serializable = {path: asdict(entry) for path, entry in self.entries.items()}
        return json.dumps(serializable, indent=2, sort_keys=True)

    def write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def read(cls, repo: Repository) -> "Index":
        path = repo.git_dir / "index"
        if not path.exists():
            return cls(repo)

        data = json.loads(path.read_text(encoding="utf-8"))
        entries = {p: IndexEntry(**meta) for p, meta in data.items()}
        return cls(repo, entries)


def read(repo: Repository) -> Index:
    """Public helper to load the index from disk."""

    return Index.read(repo)


def write(index: Index) -> None:
    """Persist the in-memory index to disk."""

    index.write()


def add(repo: Repository, files: Iterable[Path | str]) -> Index:
    """Stage one or more paths, returning the updated index."""

    idx = read(repo)
    for file_path in files:
        idx.add(file_path)
    write(idx)
    return idx

