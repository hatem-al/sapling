from pathlib import Path

from sappling.repository import Repository


def test_init_creates_git_directory(tmp_path: Path) -> None:
    repo = Repository(tmp_path)
    repo.init()

    git_dir = tmp_path / ".git"
    assert git_dir.exists()
    assert (git_dir / "objects").is_dir()
    assert (git_dir / "refs/heads").is_dir()
    assert (git_dir / "refs/tags").is_dir()
    assert (git_dir / "HEAD").read_text() == "ref: refs/heads/master\n"
