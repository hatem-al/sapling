# Architecture

Sapling mirrors Git's plumbing layer closely enough that objects produced by either tool are byte-for-byte identical for the same input. This document explains how the five modules fit together.

---

## Module Map

```
src/sapling/
├── repository.py   — worktree + .git path handle
├── objects.py      — SHA-1 content-addressable store
├── index.py        — JSON staging area
├── plumbing.py     — trees, commits, refs, merge, status, diff
└── cli.py          — argparse porcelain (thin wrapper over plumbing)
```

Data flows from CLI → plumbing → objects, with the index sitting between plumbing and objects.

---

## Object Storage (`objects.py`)

Every piece of content is stored as a **loose object** under `.git/objects/aa/bbcc…` where `aa` is the first byte of the SHA-1 hex digest.

The on-disk format matches Git exactly:

```
zlib( "type len\0payload" )
```

- **Blob**: payload is raw file bytes
- **Tree**: payload is concatenated entries of `"mode name\0" + 20-byte-sha`
- **Commit**: payload is a plaintext header block + blank line + message

Because the format is identical to Git's, you can point `git cat-file -p <sha>` at any object Sapling writes and it will parse it correctly — and vice versa.

`hash_object(data, write=True)` is the single write path. `read_object(oid)` is the single read path. Nothing else touches `.git/objects/` directly.

---

## Staging Area (`index.py`)

Git uses a binary index format optimized for speed. Sapling uses **JSON** at `.git/index` for transparency:

```json
{
  "hello.txt": {
    "mode": 33188,
    "mtime": 1714000000.0,
    "oid":  "ce013625030ba8dba906f756967f9e9ca394464a",
    "path": "hello.txt",
    "size": 12
  }
}
```

`IndexEntry` is a frozen dataclass. `Index` is the in-memory container. Module-level `add()` and `read()` are the public interface used by plumbing — nothing else reads or writes the index file directly.

---

## Trees, Commits, and Refs (`plumbing.py`)

**write_tree** walks `index.entries`, builds a nested dict mirroring the directory structure, then recursively writes tree objects bottom-up via `hash_object`.

**commit_tree** serializes the Git commit format (tree, parent, author, committer, message), calls `hash_object`, and returns the new commit SHA.

**Refs** are plain text files: `.git/refs/heads/<branch>` contains a 40-char hex OID. `HEAD` is either `ref: refs/heads/<branch>` (attached) or a bare OID (detached).

**Merge** (`merge_branch`) follows this path:
1. Attempt fast-forward: if HEAD is an ancestor of target, just advance the ref and rewrite the worktree.
2. Otherwise find the common ancestor (`find_merge_base` — BFS through parent pointers collecting the ancestor set of one side, then walking the other until a match is found).
3. Build flat path→entry maps for base, ours, theirs trees.
4. For each path: if only one side changed, take that side. If both changed identically, no-op. If both changed differently, write a conflict file with `<<<<<<< HEAD` / `=======` / `>>>>>>> branch` markers.
5. Re-snapshot the working tree into the index and write it.

---

## CLI (`cli.py`)

Each subcommand is a straightforward if-block that constructs a `Repository`, calls into `plumbing` or `objects`, and prints a result. No business logic lives here.

`Repository` is a frozen dataclass with one field (`worktree: Path`) and one derived property (`git_dir = worktree / ".git"`). It is passed by value everywhere — nothing mutates it.

---

## Key Design Decisions

| Decision | Why |
|---|---|
| JSON index instead of binary | Instant inspectability with `cat .git/index`; dramatically speeds up debugging merge state |
| Loose objects only (no pack files) | Keeps object I/O to two functions; pack files are a performance optimization orthogonal to learning the model |
| First-parent walk in `log` | Matches the common case and avoids needing a topological sort |
| `GIT_AUTHOR_NAME` / `GIT_COMMITTER_NAME` env vars | Same as Git; lets integration tests set deterministic author identity |
| `master` as default branch | Matches Git's historical default; avoids confusing learners comparing output |
