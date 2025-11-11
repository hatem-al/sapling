# Architecture

Sappling follows Git's plumbing closely. Each module corresponds to a storage or porcelain layer.

```mermaid
graph TD
    WT[Working Tree]
    IDX[Index (JSON)]
    OBJ[Object Store]
    REFS[Refs / HEAD]

    WT -- hash/add --> IDX
    IDX -- write_tree --> OBJ
    OBJ -- commit --> REFS
    REFS -- checkout --> WT
    REFS -- merge --> WT
    OBJ -- cat-file/status/diff --> WT
```

## Modules

- `sappling.objects`: SHA-1 hashing + zlib compression into `.git/objects/aa/bb...`
- `sappling.index`: JSON index capturing `path/mode/mtime/size/oid` to mimic Git's staging area.
- `sappling.plumbing`: tree assembly, commit authoring, refs, status/diff, and merge logic.
- `sappling.cli`: porcelain commands wired via `argparse`.

## Object Model

Every loose object is stored as `type size\0payload`. The `hash_object` helper builds this canonical format so the SHA-1 and on-disk bytes are Git-compatible.

- **Blobs:** `blob <len>\0<data>`
- **Trees:** concatenated entries of `mode name\0<20-byte sha>`; directories get mode `40000`.
- **Commits:** plaintext metadata referencing a tree and parents, ending with a blank line and the commit message.

## Design Decisions

1. **JSON Index:** favors readability and easy diffs during development; we can swap to the binary index later.
2. **Loose Objects Only:** packfiles add complexity and aren't necessary for learning. Git-compatible storage ensures future packfile work is feasible.
3. **Merge Strategy:** first-parent three-way merge with conflict markers is enough for demos; advanced features (rename detection, recursive strategies) are deferred.
4. **No Network Layer:** Sappling intentionally omits remote operations to keep the scope focused on local history mechanics.
