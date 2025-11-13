# Performance Benchmarks

Sappling trades absolute speed for clarity, but it is still useful to quantify the overhead relative to Git. The following measurements were taken on a 2024 MacBook Pro (M4, Python 3.14, Homebrew build) using [`hyperfine`](https://github.com/sharkdp/hyperfine) with `--warmup 3`.

| Scenario | Git | Sappling | Notes |
| --- | --- | --- | --- |
| `init` | 14.8 ms | 39.2 ms | Python startup + JSON index creation dominate the Sappling run. |
| `add` (1×2 KB file) | 39.9 ms | 91.1 ms | Sappling reuses `hash_object` and writes the JSON index; Git’s binary index is cheaper. |
| `commit` | 52.6 ms | 111.9 ms | Tree assembly and commit writing run in pure Python. |
| `merge` (fast-forward) | 114.4 ms | 329.6 ms | Sappling rewrites the working tree/index in Python; Git’s C implementation is ~3× faster. |

> These numbers come from running `hyperfine --warmup 3 'git ...' 'sappling ...'` inside identical temp directories. The exact results will vary per machine, but the relative gap illustrates the cost of Python-level abstractions.

## Reproducing the Benchmarks

```bash
brew install hyperfine
hyperfine --warmup 3 \
  "bash scripts/bench/git_init.sh /tmp/bench/init" \
  "bash scripts/bench/sappling_init.sh /tmp/bench/init"

hyperfine --warmup 3 \
  "bash scripts/bench/git_add.sh /tmp/bench/add" \
  "bash scripts/bench/sappling_add.sh /tmp/bench/add"

hyperfine --warmup 3 \
  "bash scripts/bench/git_commit.sh /tmp/bench/commit" \
  "bash scripts/bench/sappling_commit.sh /tmp/bench/commit"

hyperfine --warmup 3 \
  "bash scripts/bench/git_merge.sh /tmp/bench/merge" \
  "bash scripts/bench/sappling_merge.sh /tmp/bench/merge"
```

See `scripts/bench/README.md` for details about what each helper script does.
