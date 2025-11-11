# Sappling vs. Git

Sappling deliberately mirrors Git's object database so that each command is easy to cross-check against the real tool. The table below summarizes the current parity.

| Capability | Sappling | Git | Notes |
| --- | --- | --- | --- |
| Object storage | ✅ | ✅ | Uses identical `type size\0payload` format and zlib compression, so blob/tree/commit IDs match Git for the same contents. |
| Index/staging | ✅ (JSON) | ✅ (binary) | Sappling writes a JSON index for readability; Git's binary index is more compact and stores stage bits. |
| Branch refs | ✅ | ✅ | Stored under `.git/refs/heads/<name>` with the same text files as Git. |
| Checkout | ✅ | ✅ | Sappling rewrites the working tree from commit trees; it currently skips dirty-worktree checks and sparse checkout features. |
| Merge | ✅ (FF + recursive w/ conflict markers) | ✅ (full suite) | Sappling implements fast-forward detection and a first-parent three-way merge. Git handles octopus merges, rename detection, etc. |
| Status / diff | ✅ | ✅ | Sappling's output is intentionally terse. Git tracks rename detection, submodules, and colorized diffs. |
| Packfiles | ❌ | ✅ | Sappling only writes loose objects today. |
| Reflog & GC | ❌ | ✅ | Planned future work once the core porcelain solidifies. |

## How to Compare Output

You can run the same workflow with both tools and compare SHA-1s:

```bash
TMP=$(mktemp -d)
cd "$TMP"

git init git-repo
sappling init sap-repo

cp ../scripts/demo.sh demo.sh
(cd git-repo && bash ../demo.sh)
(cd sap-repo && bash ../demo.sh)

cd git-repo
find .git/objects -type f | sort > ../git-objects.txt

cd ../sap-repo
find .git/objects -type f | sort > ../sap-objects.txt

cd ..
diff git-objects.txt sap-objects.txt
```

When both repos ingest the same files (ignoring packfiles), the object sets should match.
