---
name: testing-m3utool
description: Test the m3utool CLI end-to-end. Use when verifying m3utool parser, validator, sanitizer, transform, or checker changes.
---

# Testing m3utool CLI

## Setup

```bash
cd ~/ADULTI
pip install -e ".[dev]"
m3utool --version  # verify CLI is available
```

## Running Unit Tests

```bash
python -m pytest -q
```

## Linting

```bash
python -m ruff check .
```

## End-to-End CLI Testing

All testing is shell-based (no GUI). Do NOT record — capture command output as text evidence.

### Create Test Fixtures

Create M3U files under `/tmp/m3u-test/` with:
1. **good.m3u** — clean playlist with 3+ valid entries, different `group-title` values
2. **bad.m3u** — playlist with: duplicate names, duplicate URLs, a malformed URL (`http://`), an empty title, a malformed `#EXTINF` line (missing comma)
3. **creds.m3u** — playlist with credentials in: (a) userinfo (`user:pass@host`), (b) query params (`?username=X&token=Y`), (c) path segments (`/USER/PASS/id`)

### Subcommand Test Patterns

| Subcommand | Key assertions |
|---|---|
| `validate` clean | Exit code 0, `0 issue(s)`, no `[error]` lines |
| `validate` bad | Exit code 1, `[error]` for malformed URL, `[warning]` for duplicates |
| `validate --strict` | Exit code 2 on parse error (malformed #EXTINF) |
| `sanitize` | Exit 0, output file has no literal credentials, `.env` has extracted values |
| `sanitize --path-credentials N` | First N path segments replaced with `${M3U_*}`, stream IDs preserved |
| `format` | Exit 0, fewer #EXTINF lines (deduped), sorted by group-title |
| `check` | Output has `alive`/`dead`/`skipped` labels, stderr summary with counts |
| missing file | Exit code 2, stderr: `error: file not found` |

### Known Edge Cases

- **Placeholder caching bug (fixed in PR #2):** When `--path-credentials` is used and two entries share the same path-segment value, verify the second entry's URL has `${VAR}` wrapping (not just `VAR`). This was caused by `_SecretStore.placeholder()` caching the raw name instead of the full `${name}` string.
- **Lenient vs strict parsing:** In lenient mode (default), malformed `#EXTINF` lines are silently skipped. In strict mode, the first error causes exit code 2. Test both modes.
- **example.com URLs return HTTP 404** — useful for testing the `check` command (expect `dead` status and exit code 1).

## Devin Secrets Needed

None — m3utool is a pure CLI tool with no external service dependencies.
