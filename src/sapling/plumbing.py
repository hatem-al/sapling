"""Higher-level plumbing helpers for trees, commits, refs, and worktree state."""

from __future__ import annotations

import difflib
import os
import shutil
import time
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

from . import index
from .objects import hash_object, read_object
from .repository import Repository


# --------------------------------------------------------------------------------------
# Trees and commits


def write_tree(repo: Repository) -> str:
    """Materialize the current index into Git tree objects."""

    idx = index.read(repo)
    tree_data = _build_tree(idx.entries)
    return _write_tree_recursive(repo, tree_data)


def commit_tree(
    repo: Repository,
    tree_sha: str,
    parents: list[str] | tuple[str, ...] | str | None,
    message: str,
) -> str:
    """Create a commit object pointing to `tree_sha` with optional parents."""

    now = int(time.time())
    tz = time.strftime("%z", time.localtime(now))

    author_name = os.getenv("GIT_AUTHOR_NAME") or os.getenv("GIT_COMMITTER_NAME") or "Sapling User"
    author_email = os.getenv("GIT_AUTHOR_EMAIL") or os.getenv("GIT_COMMITTER_EMAIL") or "user@example.com"
    committer_name = os.getenv("GIT_COMMITTER_NAME") or author_name
    committer_email = os.getenv("GIT_COMMITTER_EMAIL") or author_email

    message = message.rstrip("\n") + "\n"
    lines = [f"tree {tree_sha}\n"]

    if parents:
        if isinstance(parents, str):
            parent_list = [parents]
        else:
            parent_list = list(parents)
        for parent in parent_list:
            lines.append(f"parent {parent}\n")
    lines.append(f"author {author_name} <{author_email}> {now} {tz}\n")
    lines.append(f"committer {committer_name} <{committer_email}> {now} {tz}\n")
    lines.append("\n")
    lines.append(message)

    payload = "".join(lines).encode()
    return hash_object(payload, obj_type="commit", repo=repo)


def parse_commit(repo: Repository, oid: str) -> dict:
    """Return a parsed representation of the commit identified by `oid`."""

    obj_type, data = read_object(oid, repo=repo)
    if obj_type != "commit":
        raise ValueError(f"Object {oid} is not a commit (found {obj_type})")

    header_raw, _, message = data.partition(b"\n\n")
    message_text = message.decode("utf-8", errors="replace")
    commit: dict = {"oid": oid, "message": message_text, "parents": []}

    for line in header_raw.decode().splitlines():
        key, value = line.split(" ", 1)
        if key == "tree":
            commit["tree"] = value
        elif key == "parent":
            commit.setdefault("parents", []).append(value)
        elif key in {"author", "committer"}:
            name_email, ts, tz = value.rsplit(" ", 2)
            commit[key] = {"ident": name_email, "timestamp": int(ts), "timezone": tz}
        else:
            commit[key] = value

    return commit


def walk_commits(repo: Repository, start_oid: str | None):
    """Yield commits starting at `start_oid`, following first parents."""

    current = start_oid
    while current:
        commit = parse_commit(repo, current)
        yield commit
        parents = commit.get("parents") or []
        current = parents[0] if parents else None


# --------------------------------------------------------------------------------------
# Reference helpers


def get_head_commit(repo: Repository) -> Tuple[str | None, str | None]:
    """Return (ref, oid) for the current HEAD."""

    head_path = repo.git_dir / "HEAD"
    data = head_path.read_text(encoding="utf-8").strip()

    if data.startswith("ref: "):
        ref = data[5:]
        ref_path = repo.git_dir / ref
        if ref_path.exists():
            return ref, ref_path.read_text(encoding="utf-8").strip()
        return ref, None

    return None, data or None


def get_current_branch(repo: Repository) -> str | None:
    ref, _ = get_head_commit(repo)
    if ref and ref.startswith("refs/heads/"):
        return ref.split("/", 2)[-1]
    return None


def update_ref(repo: Repository, ref: str, oid: str) -> None:
    """Update the given ref to point at `oid`."""

    ref_path = repo.git_dir / ref
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    ref_path.write_text(f"{oid}\n", encoding="utf-8")


def create_branch(repo: Repository, name: str, start_oid: str) -> None:
    ref = f"refs/heads/{name}"
    ref_path = repo.git_dir / ref
    if ref_path.exists():
        raise ValueError(f"Branch {name} already exists")
    update_ref(repo, ref, start_oid)


def list_branches(repo: Repository) -> Iterable[str]:
    heads_dir = repo.git_dir / "refs" / "heads"
    if not heads_dir.exists():
        return []
    return sorted(p.name for p in heads_dir.iterdir() if p.is_file())


def set_head(repo: Repository, ref: str) -> None:
    (repo.git_dir / "HEAD").write_text(f"ref: {ref}\n", encoding="utf-8")


# --------------------------------------------------------------------------------------
# Merge helpers


def is_ancestor(repo: Repository, ancestor: str, descendant: str) -> bool:
    if ancestor == descendant:
        return True

    visited: Set[str] = set()
    stack = [descendant]
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        if current == ancestor:
            return True
        commit = parse_commit(repo, current)
        stack.extend(commit.get("parents", []))
    return False


def find_merge_base(repo: Repository, oid_a: str, oid_b: str) -> str | None:
    ancestors_a = _collect_ancestors(repo, oid_a)
    queue = [oid_b]
    visited: Set[str] = set()

    while queue:
        current = queue.pop(0)
        if current in ancestors_a:
            return current
        if current in visited:
            continue
        visited.add(current)
        commit = parse_commit(repo, current)
        queue.extend(commit.get("parents", []))
    return None


def fast_forward_merge(repo: Repository, target_branch: str) -> bool:
    current_ref, head_oid = get_head_commit(repo)
    target_oid = get_branch_commit(repo, target_branch)

    if not target_oid:
        raise ValueError(f"Branch {target_branch} does not exist")
    if not head_oid:
        raise ValueError("Current branch has no commits to merge")
    if not current_ref:
        raise ValueError("Cannot fast-forward a detached HEAD")

    if not is_ancestor(repo, head_oid, target_oid):
        return False

    commit = parse_commit(repo, target_oid)
    tree_sha = commit.get("tree")
    if tree_sha:
        checkout_tree(repo, tree_sha)
    update_ref(repo, current_ref, target_oid)
    return True


def merge_branch(repo: Repository, branch: str) -> dict:
    status = get_status(repo)
    if any(status.values()):
        raise ValueError("Working tree is not clean; commit or stash changes before merging")

    current_ref, head_oid = get_head_commit(repo)
    target_oid = get_branch_commit(repo, branch)
    if not target_oid:
        raise ValueError(f"Branch {branch} does not exist")
    if not head_oid:
        raise ValueError("Current branch has no commits to merge")

    result: dict = {"fast_forward": False, "conflicts": [], "commit": None}

    if fast_forward_merge(repo, branch):
        result["fast_forward"] = True
        result["commit"] = target_oid
        return result

    merge_base = find_merge_base(repo, head_oid, target_oid)
    base_tree = _tree_sha_from_commit(repo, merge_base)
    ours_tree = _tree_sha_from_commit(repo, head_oid)
    theirs_tree = _tree_sha_from_commit(repo, target_oid)

    conflicts = _three_way_merge_trees(repo, base_tree, ours_tree, theirs_tree, branch)
    if conflicts:
        result["conflicts"] = conflicts
        return result

    tree_sha = write_tree(repo)
    commit_sha = commit_tree(
        repo,
        tree_sha,
        parents=[head_oid, target_oid],
        message=f"Merge branch '{branch}'",
    )
    if current_ref:
        update_ref(repo, current_ref, commit_sha)
    else:
        (repo.git_dir / "HEAD").write_text(f"{commit_sha}\n", encoding="utf-8")

    result["commit"] = commit_sha
    return result


def get_branch_commit(repo: Repository, branch: str) -> str | None:
    ref_path = repo.git_dir / "refs" / "heads" / branch
    if not ref_path.exists():
        return None
    return ref_path.read_text(encoding="utf-8").strip()


# --------------------------------------------------------------------------------------
# Checkout helpers
# --------------------------------------------------------------------------------------
# Checkout helpers


def checkout_branch(repo: Repository, branch: str) -> str:
    """Set HEAD to `branch` and populate worktree from its commit."""

    branch_oid = get_branch_commit(repo, branch)
    if not branch_oid:
        raise ValueError(f"Branch {branch} does not exist")

    commit = parse_commit(repo, branch_oid)
    tree_sha = commit.get("tree")
    if not tree_sha:
        raise ValueError(f"Commit {branch_oid} missing tree pointer")

    set_head(repo, f"refs/heads/{branch}")
    checkout_tree(repo, tree_sha)
    return branch_oid


def checkout_tree(repo: Repository, tree_sha: str) -> None:
    """Replace the working directory contents with the given tree."""

    _clear_worktree(repo)
    entries: Dict[str, index.IndexEntry] = {}
    _restore_tree(repo, tree_sha, Path(), entries)
    new_index = index.Index(repo, entries)
    new_index.write()


# --------------------------------------------------------------------------------------
# Status & diff helpers


def get_status(repo: Repository) -> dict:
    idx = index.read(repo)
    index_entries = idx.entries
    head_tree = _head_tree_map(repo)
    worktree_files = _worktree_files(repo)

    staged: List[str] = []
    modified: List[str] = []
    tracked_paths = set(index_entries.keys())

    for path, entry in index_entries.items():
        file_path = repo.worktree / path
        if file_path.exists():
            data = file_path.read_bytes()
            oid = hash_object(data, write=False)
            if oid != entry.oid:
                modified.append(path)
        else:
            modified.append(path)

        head_entry = head_tree.get(path)
        if head_entry is None or head_entry["oid"] != entry.oid:
            staged.append(path)

    untracked = sorted(p for p in worktree_files if p not in tracked_paths)

    return {
        "staged": sorted(set(staged)),
        "modified": sorted(set(modified)),
        "untracked": untracked,
    }


def generate_diff(repo: Repository, *, staged: bool = False, paths: Iterable[str] | None = None) -> str:
    idx = index.read(repo)
    index_entries = idx.entries
    head_tree = _head_tree_map(repo)

    targets = paths or index_entries.keys()
    diffs: List[str] = []
    for path in targets:
        path = str(path)
        if path not in index_entries and not staged:
            continue

        if staged:
            base_entry = head_tree.get(path)
            target_entry = index_entries.get(path)
            if not target_entry:
                continue
            base_content = _blob_content(repo, base_entry["oid"]) if base_entry else b""
            new_content = _blob_content(repo, target_entry.oid)
            from_label = f"a/{path}"
            to_label = f"b/{path}"
        else:
            entry = index_entries.get(path)
            if not entry:
                continue
            base_content = _blob_content(repo, entry.oid)
            work_path = repo.worktree / path
            if not work_path.exists():
                new_content = b""
            else:
                new_content = work_path.read_bytes()
            from_label = f"a/{path}"
            to_label = f"b/{path}"

        if base_content == new_content:
            continue

        diff = difflib.unified_diff(
            base_content.decode("utf-8", errors="replace").splitlines(),
            new_content.decode("utf-8", errors="replace").splitlines(),
            fromfile=from_label,
            tofile=to_label,
            lineterm="",
        )
        diffs.append("\n".join(diff))

    return "\n\n".join(d for d in diffs if d)


# --------------------------------------------------------------------------------------
# Internal helpers


def _build_tree(entries: Dict[str, index.IndexEntry]) -> Dict[str, object]:
    root: Dict[str, object] = {}
    for entry in entries.values():
        parts = Path(entry.path).parts
        node = root
        for part in parts[:-1]:
            node = node.setdefault(part, {})  # type: ignore[assignment]
        node[parts[-1]] = entry  # type: ignore[index]
    return root


def _write_tree_recursive(repo: Repository, tree: Dict[str, object]) -> str:
    chunks = []
    for name in sorted(tree.keys()):
        child = tree[name]
        if isinstance(child, index.IndexEntry):
            mode = f"{child.mode:o}"
            oid = child.oid
        else:
            oid = _write_tree_recursive(repo, child)  # type: ignore[arg-type]
            mode = "40000"
        entry = f"{mode} {name}".encode() + b"\x00" + bytes.fromhex(oid)
        chunks.append(entry)
    data = b"".join(chunks)
    return hash_object(data, obj_type="tree", repo=repo)


def _iter_tree_entries(repo: Repository, tree_sha: str):
    obj_type, data = read_object(tree_sha, repo=repo)
    if obj_type != "tree":
        raise ValueError(f"Object {tree_sha} is not a tree")

    i = 0
    while i < len(data):
        end = data.find(b"\x00", i)
        header = data[i:end].decode()
        mode_str, name = header.split(" ", 1)
        oid = data[end + 1 : end + 21].hex()
        yield mode_str, name, oid
        i = end + 21


def _restore_tree(
    repo: Repository,
    tree_sha: str,
    base: Path,
    collected: Dict[str, index.IndexEntry],
) -> None:
    for mode_str, name, oid in _iter_tree_entries(repo, tree_sha):
        rel_path = base / name
        if mode_str == "40000":
            target_dir = repo.worktree / rel_path
            target_dir.mkdir(parents=True, exist_ok=True)
            _restore_tree(repo, oid, rel_path, collected)
        else:
            obj_type, data = read_object(oid, repo=repo)
            if obj_type != "blob":
                raise ValueError(f"Tree entry {rel_path} points to non-blob {oid}")
            target_file = repo.worktree / rel_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_bytes(data)
            stat_result = target_file.stat()
            entry = index.IndexEntry(
                path=str(rel_path),
                mode=int(mode_str, 8),
                mtime=stat_result.st_mtime,
                size=stat_result.st_size,
                oid=oid,
            )
            collected[str(rel_path)] = entry


def _clear_worktree(repo: Repository) -> None:
    for child in repo.worktree.iterdir():
        if child.name == ".git":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _head_tree_map(repo: Repository) -> Dict[str, dict]:
    _, head = get_head_commit(repo)
    if not head:
        return {}
    commit = parse_commit(repo, head)
    tree_sha = commit.get("tree")
    if not tree_sha:
        return {}
    result: Dict[str, dict] = {}
    _collect_tree(repo, tree_sha, Path(), result)
    return result


def _collect_tree(repo: Repository, tree_sha: str, base: Path, collected: Dict[str, dict]) -> None:
    for mode_str, name, oid in _iter_tree_entries(repo, tree_sha):
        rel_path = base / name
        if mode_str == "40000":
            _collect_tree(repo, oid, rel_path, collected)
        else:
            collected[str(rel_path)] = {"mode": mode_str, "oid": oid}


def _worktree_files(repo: Repository) -> List[str]:
    files: List[str] = []
    for path in repo.worktree.rglob("*"):
        if path.is_dir():
            continue
        try:
            path.relative_to(repo.git_dir)
            continue
        except ValueError:
            pass
        rel = path.relative_to(repo.worktree)
        files.append(str(rel))
    return sorted(files)


def _blob_content(repo: Repository, oid: str) -> bytes:
    obj_type, data = read_object(oid, repo=repo)
    if obj_type != "blob":
        raise ValueError(f"Object {oid} is not a blob")
    return data


def _collect_ancestors(repo: Repository, start: str) -> Set[str]:
    ancestors: Set[str] = set()
    stack = [start]
    while stack:
        current = stack.pop()
        if current in ancestors:
            continue
        ancestors.add(current)
        commit = parse_commit(repo, current)
        stack.extend(commit.get("parents", []))
    return ancestors


def _tree_sha_from_commit(repo: Repository, commit_oid: str | None) -> str | None:
    if not commit_oid:
        return None
    commit = parse_commit(repo, commit_oid)
    return commit.get("tree")


def _tree_map(repo: Repository, tree_sha: str | None) -> Dict[str, dict]:
    if not tree_sha:
        return {}
    collected: Dict[str, dict] = {}
    _collect_tree(repo, tree_sha, Path(), collected)
    return collected


def _three_way_merge_trees(
    repo: Repository,
    base_tree: str | None,
    ours_tree: str | None,
    theirs_tree: str | None,
    branch: str,
) -> List[str]:
    base_map = _tree_map(repo, base_tree)
    ours_map = _tree_map(repo, ours_tree)
    theirs_map = _tree_map(repo, theirs_tree)

    all_paths = sorted(set(base_map) | set(ours_map) | set(theirs_map))
    idx = index.read(repo)
    conflicts: List[str] = []

    for path in all_paths:
        base_entry = base_map.get(path)
        ours_entry = ours_map.get(path)
        theirs_entry = theirs_map.get(path)
        action, entry = _select_entry(base_entry, ours_entry, theirs_entry)

        if action == "conflict":
            _write_conflict_file(repo, path, ours_entry, theirs_entry, branch)
            conflicts.append(path)
            continue

        if action == "delete" or entry is None:
            idx.entries.pop(path, None)
            _delete_path(repo, path)
            continue

        target_file = repo.worktree / path

        if action == "theirs":
            data = _blob_content(repo, entry["oid"])
            _write_file(repo, path, data)
        elif action == "ours":
            if not (repo.worktree / path).exists():
                data = _blob_content(repo, entry["oid"])
                _write_file(repo, path, data)

        idx.entries[path] = _index_entry_from_file(repo, path, entry["mode"], entry["oid"])

    idx.write()
    return conflicts


def _select_entry(base, ours, theirs):
    if ours is None and theirs is None:
        return "delete", None
    if _entries_equal(ours, theirs):
        return "ours", ours
    if _entries_equal(ours, base):
        return ("theirs", theirs)
    if _entries_equal(theirs, base):
        return ("ours", ours)
    if theirs is None and ours is not None:
        return ("ours", ours)
    if ours is None and theirs is not None:
        return ("theirs", theirs)
    return "conflict", None


def _entries_equal(entry_a, entry_b) -> bool:
    if entry_a is entry_b:
        return True
    if entry_a is None or entry_b is None:
        return entry_a is None and entry_b is None
    return entry_a["oid"] == entry_b["oid"] and entry_a["mode"] == entry_b["mode"]


def _write_conflict_file(repo: Repository, path: str, ours, theirs, branch: str) -> None:
    ours_data = _blob_content(repo, ours["oid"]) if ours else b""
    theirs_data = _blob_content(repo, theirs["oid"]) if theirs else b""
    content = _format_conflict(ours_data, theirs_data, branch)
    _write_file(repo, path, content)


def _write_file(repo: Repository, path: str, data: bytes) -> None:
    target = repo.worktree / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def _delete_path(repo: Repository, path: str) -> None:
    target = repo.worktree / path
    if target.exists():
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    parent = target.parent
    while parent != repo.worktree and parent.exists() and not any(parent.iterdir()):
        parent.rmdir()
        parent = parent.parent


def _index_entry_from_file(repo: Repository, path: str, mode_str: str, oid: str) -> index.IndexEntry:
    target = repo.worktree / path
    stat_result = target.stat()
    return index.IndexEntry(
        path=path,
        mode=int(mode_str, 8),
        mtime=stat_result.st_mtime,
        size=stat_result.st_size,
        oid=oid,
    )


def _format_conflict(ours: bytes, theirs: bytes, branch: str) -> bytes:
    ours_text = ours.decode("utf-8", errors="replace")
    theirs_text = theirs.decode("utf-8", errors="replace")
    return (
        "<<<<<<< HEAD\n"
        f"{ours_text}"
        "\n=======\n"
        f"{theirs_text}"
        f"\n>>>>>>> {branch}\n"
    ).encode("utf-8")
