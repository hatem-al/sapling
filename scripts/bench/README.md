# Benchmark Helpers

Each script resets a temporary directory, runs the named operation once, and exits. Pair these with `hyperfine` to compare Git vs Sapling.

Examples:

```bash
hyperfine --warmup 3 \
  "bash scripts/bench/git_init.sh /tmp/bench/init" \
  "bash scripts/bench/sapling_init.sh /tmp/bench/init"

hyperfine --warmup 3 \
  "bash scripts/bench/git_commit.sh /tmp/bench/commit" \
  "bash scripts/bench/sapling_commit.sh /tmp/bench/commit"
```

Scripts available:

- `git_init.sh` / `sapling_init.sh`
- `git_add.sh` / `sapling_add.sh`
- `git_commit.sh` / `sapling_commit.sh`
- `git_merge.sh` / `sapling_merge.sh`

Feel free to extend them with larger repositories or additional operations.
