"""Repository primitives mirroring Git's .git directory layout."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Repository:
    """Lightweight handle around a working tree and its .git metadata."""

    worktree: Path

    @property
    def git_dir(self) -> Path:
        return self.worktree / ".git"

    def init(self, *, force: bool = False) -> None:
        """Initialize a bare-bones .git directory structure.

        Parameters
        ----------
        force:
            Overwrite an existing .git directory if true.
        """

        if not self.worktree.exists():
            raise FileNotFoundError(f"Worktree {self.worktree} does not exist")

        if self.git_dir.exists() and not force:
            raise FileExistsError(f"Repository already initialized at {self.git_dir}")

        _mkdir(self.git_dir)
        for rel in ("objects", "refs/heads", "refs/tags"):  # match Git's storage layout
            _mkdir(self.git_dir / rel)

        head = self.git_dir / "HEAD"
        head.write_text("ref: refs/heads/master\n", encoding="utf-8")


def _mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
