# Benchmark Helpers

Each script resets a temporary directory, runs the named operation once, and exits. Pair these with `hyperfine` to compare Git vs Sappling.

Examples:

```bash
hyperfine --warmup 3 \
  "bash scripts/bench/git_init.sh /tmp/bench/init" \
  "bash scripts/bench/sappling_init.sh /tmp/bench/init"

hyperfine --warmup 3 \
  "bash scripts/bench/git_commit.sh /tmp/bench/commit" \
  "bash scripts/bench/sappling_commit.sh /tmp/bench/commit"
```

Scripts available:

- `git_init.sh` / `sappling_init.sh`
- `git_add.sh` / `sappling_add.sh`
- `git_commit.sh` / `sappling_commit.sh`
- `git_merge.sh` / `sappling_merge.sh`

Feel free to extend them with larger repositories or additional operations.
