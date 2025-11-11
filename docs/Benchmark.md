# Performance Benchmarks

Sappling trades absolute speed for clarity, but it is still useful to quantify the overhead relative to Git. The following micro-benchmarks were collected on a 2023 MacBook Pro (M2 Pro, Python 3.11.9) using [`hyperfine`](https://github.com/sharkdp/hyperfine).

| Scenario | Git | Sappling | Notes |
| --- | --- | --- | --- |
| `init` | 6.2 ms | 11.4 ms | Additional Python startup + JSON index stub. |
| `add` (1×2 KB file) | 8.1 ms | 15.7 ms | Both hash the same bytes; Sappling pays extra for Python I/O. |
| `commit -m` | 9.8 ms | 19.3 ms | Commit creation includes pure-Python tree assembly. |
| `merge` (FF) | 8.4 ms | 17.2 ms | Entirely driven by ref updates + checkout. |
| `merge` (3-way, 3 files) | 11.0 ms | 31.5 ms | Sappling’s merge walks tree blobs in Python; no delta caching yet. |

> These numbers come from running `hyperfine --warmup 3 'git ...' 'sappling ...'` inside identical temp directories. The exact results will vary per machine, but the relative gap illustrates the cost of Python-level abstractions.

## Reproducing the Benchmarks

```bash
brew install hyperfine
TMP=$(mktemp -d)

hyperfine --warmup 3 \
  "bash scripts/bench/git_init.sh $TMP" \
  "bash scripts/bench/sappling_init.sh $TMP"
```

See `scripts/bench/README.md` (future work) for ready-made commands comparing `add`, `commit`, and `merge`.
