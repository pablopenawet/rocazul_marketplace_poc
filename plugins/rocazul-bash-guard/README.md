# bash-guard

Two-stage guard for Claude Code's Bash tool. Auto-allows commands clearly bounded to the project, asks the user for anything risky.

## How it works

Both hooks run as `PreToolUse` on every Bash invocation, in order:

1. **`bash-guard.py`** — fast static check (no network). Categorizes commands as `allow`, `ask`, or `uncertain` based on:
   - Safe read-only commands (`ls`, `cat`, `grep`, …) → **allow**
   - Write commands with paths inside project / `/tmp` / `~/.claude` → **allow**
   - Write commands targeting paths outside allowed dirs → **ask**
   - Dangerous patterns (`sudo`, `curl | sh`, `dd of=/dev/…`, fork bombs) → **ask**
   - `git push` → **ask**; other `git …` → **allow**
   - Anything unrecognized → **uncertain** (defers to layer 2)

2. **`bash-guard-llm.py`** — only matters when layer 1 returns `uncertain`. Sends the command (and the script body, if any) to a Claude model (Haiku 4.5 by default) with a detailed safety prompt. Model returns `allow`, `ask`, or `deny`.
   - On error / timeout / parse failure → falls back to `ask` (never silently allows).

## Requirements

- `python3` available on `$PATH`.
- The `claude` CLI must be installed and reachable (used by the LLM hook).
  - Lookup order: `$CLAUDE_CLI` env var → `which claude` → `~/.local/bin/claude` → `~/.claude/local/claude` → `/opt/homebrew/bin/claude` → `/usr/local/bin/claude`.
- A working Claude auth (the CLI uses your local auth).

## Cost

Layer 2 invokes Haiku per uncertain command. Haiku is cheap, but not free. If you run many uncertain commands per day, costs accumulate. To reduce: expand `SAFE_COMMANDS` / `WRITE_COMMANDS` in `bash-guard.py` so more commands resolve at layer 1.

## Install

```
/plugin marketplace add jvillar/claude-plugins
/plugin install bash-guard@jvillar-claude-plugins
```

## Configuration

No config file — tweak the constants at the top of each script if you need to:

- `CLAUDE_MODEL` (default `claude-haiku-4-5`) — model used by the LLM layer.
- `CLAUDE_TIMEOUT_SECONDS` (default 35) — LLM call timeout.
- `MAX_SCRIPT_BYTES` (default 60_000) — max script body sent to LLM.
- `ALLOWED_WRITE_DIRS` in `bash-guard.py` — directories considered safe to write.

## Caveats / notes

- The plugin **never denies** at layer 1 — only `allow` / `ask` / `uncertain`. Layer 2 can `deny` only for unambiguously malicious patterns (reverse shells, fork bombs, attempts to modify the guardian itself).
- Project root is detected from `git rev-parse --show-toplevel`, falling back to `cwd`.
- The LLM prompt is intentionally strict. False positives (extra `ask`s) are preferred over false negatives.
- Compatible with macOS and Linux. Windows is untested.
