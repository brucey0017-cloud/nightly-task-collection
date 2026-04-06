# git-pulse

A zero-dependency Python 3 CLI that scans a directory tree for Git repositories and shows what needs attention first.

## What it reports

For each repo:
- path
- current branch
- ahead/behind counts (**based on local tracking refs only; no remote fetch**)
- staged / unstaged / untracked file counts
- dirty/clean state

## Usage

```bash
python3 git-pulse.py <root_path> [--depth 3] [--json]
```

Examples:

```bash
python3 git-pulse.py /root/.openclaw/workspace --depth 3
python3 git-pulse.py /root/.openclaw/workspace --depth 3 --json
```

## 30-second smoke test

Run:

```bash
python3 git-pulse.py /root/.openclaw/workspace --depth 3
```

Expected output shape:
- A `Summary:` line with total/dirty/clean counts
- A note about ahead/behind being local-tracking-only
- A table containing rows with `DIRTY`/`CLEAN`, branch, `ahead/behind`, staged/unstaged/untracked counts, and repo path

## Notes

- No third-party dependencies.
- Does not run `git fetch`.
- Nested repos inside another repo are intentionally skipped in this MVP.
