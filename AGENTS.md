# AGENTS.md: rules for AI agents working in this repository

The same rules as CLAUDE.md, for agents that read AGENTS.md.

These rules apply to any agent, whether it is helping a user clean a phone or changing the code.

## When helping a user with their phone

- Follow [PROMPT.md](PROMPT.md). Use only `python adreceipts.py <command>`.
- Never send `adb` commands that change the phone yourself. Never write scripts that do.
- Ask for explicit approval before `drill`, `apply --execute` and `restore`. `scan`, `doctor`, `plan`, `verify`, `receipts` (without screenshots) and `recheck` only read.
- Never work around a safety refusal by editing the code, the catalog or `catalog/protected.txt`.
- Screenshots need the user's consent (`--screenshots --consent`). Do not open images unless the user asks; images you read are sent to your provider.
- Never promise results. No "ad-free", no speed, battery or memory claims.
- Keep everything in `reports/` local. Use `share` before anything leaves the computer.

## When changing the code

- The core uses the Python standard library only (Python 3.9+, Windows, macOS, Linux). Pillow is an optional extra for `share --include-images`.
- Every `adb` call is an argument list sent through `adreceipts/adb.py`. Never build shell strings. Read-only commands must open adb at the `read` level.
- Every write goes through `guard` first, is logged to the journal before it happens, and is read back after.
- Do not add a way to skip the drill, the backup, the approval or guard.
- Run `python -m pytest` before committing. All tests must pass, on Windows paths too.
- Catalog entries need a public `source` URL and start as `documented`. Only a linked device report makes an entry `tested`.
- Do not copy lists or code from other projects unless the licence clearly allows it, and credit them in NOTICE.md.
- Never commit real phone output, screenshots, serial numbers, tokens, emails or local paths.
- Docs must not claim real-device testing, fixed gains, or that it works on every phone.
