"""Command-line entry point for sappling."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .objects import hash_object, read_object
from .repository import Repository
from . import index as index_mod
from .plumbing import (
    checkout_branch,
    commit_tree,
    create_branch,
    generate_diff,
    get_current_branch,
    get_head_commit,
    get_status,
    merge_branch,
    list_branches,
    update_ref,
    walk_commits,
    write_tree,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sappling", description="Educational Git clone")
    sub = parser.add_subparsers(dest="command", required=True)

    init_parser = sub.add_parser("init", help="Create a new .git directory")
    init_parser.add_argument("path", nargs="?", default=".", help="Working tree to initialize")

    hash_parser = sub.add_parser("hash-object", help="Compute and optionally store an object")
    hash_parser.add_argument("path", help="Path to the file to hash")
    hash_parser.add_argument("--type", default="blob", choices=["blob", "tree", "commit", "tag"], help="Object type header")
    hash_parser.add_argument(
        "--repo",
        default=".",
        help="Repository working tree (defaults to current directory)",
    )
    hash_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip writing the object, equivalent to git hash-object without -w",
    )

    cat_parser = sub.add_parser("cat-file", help="Display the content of an object")
    cat_parser.add_argument("oid", help="Object ID (40-hex SHA-1)")
    cat_parser.add_argument(
        "--repo",
        default=".",
        help="Repository working tree (defaults to current directory)",
    )

    add_parser = sub.add_parser("add", help="Stage files into the index")
    add_parser.add_argument("path", nargs="+", help="Files to stage")
    add_parser.add_argument(
        "--repo",
        default=".",
        help="Repository working tree (defaults to current directory)",
    )

    commit_parser = sub.add_parser("commit", help="Create a commit from the staged snapshot")
    commit_parser.add_argument("-m", "--message", required=True, help="Commit message")
    commit_parser.add_argument(
        "--repo",
        default=".",
        help="Repository working tree (defaults to current directory)",
    )

    log_parser = sub.add_parser("log", help="Display commit history")
    log_parser.add_argument(
        "--repo",
        default=".",
        help="Repository working tree (defaults to current directory)",
    )

    branch_parser = sub.add_parser("branch", help="Create or list branches")
    branch_parser.add_argument("name", nargs="?", help="Branch name to create")
    branch_parser.add_argument(
        "--repo",
        default=".",
        help="Repository working tree (defaults to current directory)",
    )

    checkout_parser = sub.add_parser("checkout", help="Switch to an existing branch")
    checkout_parser.add_argument("branch", help="Branch to check out")
    checkout_parser.add_argument(
        "--repo",
        default=".",
        help="Repository working tree (defaults to current directory)",
    )

    status_parser = sub.add_parser("status", help="Show working tree status")
    status_parser.add_argument(
        "--repo",
        default=".",
        help="Repository working tree (defaults to current directory)",
    )

    diff_parser = sub.add_parser("diff", help="Show changes between stages")
    diff_parser.add_argument(
        "--repo",
        default=".",
        help="Repository working tree (defaults to current directory)",
    )
    diff_parser.add_argument(
        "--staged",
        action="store_true",
        help="Compare index against HEAD instead of working tree",
    )
    diff_parser.add_argument("paths", nargs="*", help="Optional paths to diff")

    merge_parser = sub.add_parser("merge", help="Merge a branch into the current HEAD")
    merge_parser.add_argument("branch", help="Branch name to merge")
    merge_parser.add_argument(
        "--repo",
        default=".",
        help="Repository working tree (defaults to current directory)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        worktree = Path(args.path).resolve()
        repo = Repository(worktree)
        repo.init()
        print(f"Initialized empty sappling repository in {repo.git_dir}")
        return 0

    if args.command == "hash-object":
        file_path = Path(args.path).resolve()
        data = file_path.read_bytes()
        repo = Repository(Path(args.repo).resolve())
        git_dir = repo.git_dir
        if not git_dir.exists():
            raise FileNotFoundError(f"{git_dir} does not exist. Run 'sappling init' first.")
        oid = hash_object(data, obj_type=args.type, repo=repo, write=not args.dry_run)
        print(oid)
        return 0

    if args.command == "cat-file":
        repo = Repository(Path(args.repo).resolve())
        obj_type, body = read_object(args.oid, repo=repo)
        if obj_type == "blob":
            sys.stdout.buffer.write(body)
        else:
            # Trees/commits/tags are UTF-8 friendly; fall back to repr if not.
            try:
                sys.stdout.write(body.decode())
            except UnicodeDecodeError:
                sys.stdout.buffer.write(body)
        return 0

    if args.command == "add":
        repo = Repository(Path(args.repo).resolve())
        worktree = repo.worktree
        if not worktree.exists():
            raise FileNotFoundError(f"{worktree} does not exist. Run 'sappling init' first.")
        index_mod.add(repo, args.path)
        return 0

    if args.command == "commit":
        repo = Repository(Path(args.repo).resolve())
        git_dir = repo.git_dir
        if not git_dir.exists():
            raise FileNotFoundError(f"{git_dir} does not exist. Run 'sappling init' first.")
        tree_sha = write_tree(repo)
        ref, parent = get_head_commit(repo)
        commit_sha = commit_tree(repo, tree_sha, parents=parent, message=args.message)
        if ref:
            update_ref(repo, ref, commit_sha)
        else:
            (repo.git_dir / "HEAD").write_text(f"{commit_sha}\n", encoding="utf-8")
        summary = args.message.splitlines()[0]
        print(f"[{commit_sha[:7]}] {summary}")
        return 0

    if args.command == "log":
        repo = Repository(Path(args.repo).resolve())
        git_dir = repo.git_dir
        if not git_dir.exists():
            raise FileNotFoundError(f"{git_dir} does not exist. Run 'sappling init' first.")
        _, head = get_head_commit(repo)
        if not head:
            print("No commits yet.")
            return 0
        for commit in walk_commits(repo, head):
            author = commit.get("author", {})
            ident = author.get("ident", "unknown <unknown>")
            ts = author.get("timestamp", 0)
            tz = author.get("timezone", "+0000")
            date_str = time.strftime(
                "%a %b %d %H:%M:%S %Y",
                time.localtime(ts),
            )
            print(f"commit {commit['oid']}")
            print(f"Author: {ident}")
            print(f"Date:   {date_str} {tz}")
            message = commit.get("message", "").rstrip("\n")
            for line in message.splitlines() or [""]:
                print(f"    {line}")
            print()
        return 0

    if args.command == "branch":
        repo = Repository(Path(args.repo).resolve())
        git_dir = repo.git_dir
        if not git_dir.exists():
            raise FileNotFoundError(f"{git_dir} does not exist. Run 'sappling init' first.")
        if args.name:
            _, head = get_head_commit(repo)
            if not head:
                raise ValueError("Cannot create branch without any commits")
            create_branch(repo, args.name, head)
        else:
            current = get_current_branch(repo)
            for name in list_branches(repo):
                prefix = "*" if name == current else " "
                print(f"{prefix} {name}")
        return 0

    if args.command == "checkout":
        repo = Repository(Path(args.repo).resolve())
        git_dir = repo.git_dir
        if not git_dir.exists():
            raise FileNotFoundError(f"{git_dir} does not exist. Run 'sappling init' first.")
        checkout_branch(repo, args.branch)
        print(f"Switched to branch '{args.branch}'")
        return 0

    if args.command == "status":
        repo = Repository(Path(args.repo).resolve())
        git_dir = repo.git_dir
        if not git_dir.exists():
            raise FileNotFoundError(f"{git_dir} does not exist. Run 'sappling init' first.")
        status = get_status(repo)
        print("On branch", get_current_branch(repo) or "(detached)")
        if status["staged"]:
            print("\nChanges to be committed:")
            for path in status["staged"]:
                print(f"    {path}")
        if status["modified"]:
            print("\nChanges not staged for commit:")
            for path in status["modified"]:
                print(f"    {path}")
        if status["untracked"]:
            print("\nUntracked files:")
            for path in status["untracked"]:
                print(f"    {path}")
        if not any(status.values()):
            print("nothing to commit, working tree clean")
        return 0

    if args.command == "diff":
        repo = Repository(Path(args.repo).resolve())
        git_dir = repo.git_dir
        if not git_dir.exists():
            raise FileNotFoundError(f"{git_dir} does not exist. Run 'sappling init' first.")
        diff = generate_diff(repo, staged=args.staged, paths=args.paths or None)
        if diff:
            print(diff)
        return 0

    if args.command == "merge":
        repo = Repository(Path(args.repo).resolve())
        git_dir = repo.git_dir
        if not git_dir.exists():
            raise FileNotFoundError(f"{git_dir} does not exist. Run 'sappling init' first.")
        result = merge_branch(repo, args.branch)
        commit = result.get("commit")
        if result.get("fast_forward"):
            print(f"Fast-forward to {commit[:7] if commit else 'unknown'}")
        elif result.get("conflicts"):
            print("Automatic merge failed; fix conflicts and commit the result.")
            for path in result["conflicts"]:
                print(f"    {path}")
        else:
            print(f"Merge made commit {commit[:7] if commit else 'unknown'}")
        return 0

    parser.error("Unrecognized command")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
