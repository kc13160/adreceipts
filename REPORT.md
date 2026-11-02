# Build report

Autonomous build of AdReceipts, 2026-11-02. Choices made along the way are in [DECISIONS.md](DECISIONS.md).

## What was built

- **Program:** `adreceipts.py` and the `adreceipts/` package. It uses only the Python standard library. Commands: doctor, scan, backup, drill, plan, apply, verify, receipts, restore, recheck, share, plus catalog-check. Every command has `--help`, accepts `--adb PATH` / `ADRECEIPTS_ADB`, and returns non-zero on failure.
- **Safety layer:**
  - adb permission levels (read / screen / write), enforced in `adreceipts/adb.py`.
  - Strict argument patterns. No local shell.
  - `guard`: protected list, runtime role holders, risky names, unknown packages, uninstall rules.
  - A journal written before each change, with read-back after it.
  - Batches of at most 5, with health checks and automatic undo.
  - Undo drill required. Backup → drill → approval order, tied to a hashed device and build.
  - DNS rollback.
  - Standalone restore scripts.
- **Catalog:** `catalog/schema.json`, `catalog/xiaomi/hyperos.yml` (13 ad locations, 14 packages), `catalog/generic/android.yml` (advertising ID, Private DNS checks, 5 drill candidates, 2 DNS providers), `catalog/protected.txt`, `catalog/drill_rules.yml`, and a device report template.
  - Every entry is `documented`, with a public source: Android Authority, Notebookcheck, Gizchina, macmyths, Google, AdGuard, Mullvad, Android Developers Blog, and UAD-ng as a reference only.
  - Nothing was copied from other projects.
- **Reports:** offline HTML and Markdown for scan, plan, receipts and recheck. No external scripts or fonts. Light and dark modes, and the layout works on a phone.
- **Tests:** `tests/fake_adb.py`, a fake phone that records every command, plus 194 tests. CI is in `.github/workflows/tests.yml` (Python 3.9 to 3.13 on Ubuntu 24.04 and Windows, plus a standard-library-only job).
- **SIMULATED demo:** `demo/make_demo.py` produces `demo/sample/` (scan, plan, receipts). Every page has a SIMULATED banner, and the images are drawn fakes labelled "SIMULATED - NOT A REAL PHONE".
- **Docs:**
  - README, PROMPT, CLAUDE, AGENTS, CONTRIBUTING, SECURITY, PRIVACY, NOTICE, LICENSE (MIT, kc13160), CHANGELOG, DECISIONS, REPORT.
  - TEST_ON_PHONE (French) and LAUNCH.
  - `docs/how-it-works.md`, `docs/restore-and-recovery.md`, `docs/faq.md`.
  - Two GitHub issue forms.

## Test results

```text
python -m pytest -q          (Python 3.12.10, Windows 11, with PyYAML, jsonschema, Pillow)
194 passed in 66.31s

Python 3.11 and 3.14, pytest only (no optional packages):
175 passed, 3 skipped   (the 3 skipped tests need PyYAML/jsonschema or Pillow)

python adreceipts.py catalog-check
[OK] generic/android.yml
[OK] xiaomi/hyperos.yml
```

Python 3.9 is not installed on this computer. The code was checked with Python's 3.9 grammar (`ast.parse(feature_version=(3, 9))`), and one 3.10-only call was removed. The CI matrix runs 3.9 on GitHub (see Publication).

Tests by area:

| Area | Tests |
| --- | --- |
| guard | 42 |
| docs and claims | 38 |
| catalog | 22 |
| apply order and flags | 18 |
| review regressions | 16 |
| read-only commands | 10 |
| managed phones and devices | 10 |
| screenshots | 9 |
| failures and rollback | 8 |
| drill | 6 |
| restore | 6 |
| full run | 5 |
| share and privacy | 4 |

Every item required by section 10 has at least one test:
- No writes from scan, doctor, recheck or plan.
- guard refusals.
- apply order, device checks and dry run.
- One refusal fails the batch before any write.
- No drill skip.
- Uninstall flags and non-system refusal.
- Read-back and health failures undo the batch.
- A manufacturer block never switches method.
- Journal-only restore.
- DNS rollback.
- Screenshot consent and foreground checks.
- Share sanitizing.
- Managed phones and work profiles.
- Catalog validation, including "tested needs a report".
- A full simulated run as a real subprocess.
- Doc claims.

## Full simulated run

`tests/test_full_run.py` runs doctor, scan, backup, drill, plan (twice), apply (dry run), apply --execute, verify, receipts, recheck, restore --all, recheck and share. It drives `python adreceipts.py` as a subprocess, with `tests/fake_adb.py` as `--adb`. All steps exit with 0. Afterwards the fake phone's packages and DNS settings match the starting state.

## Section 12 review (fresh eyes, separate sub-agent)

A separate sub-agent reviewed guard, apply, drill, restore, share and the modules they rely on. Its question was how they could damage a phone or leak data. It found 12 issues. Findings 1 to 11 were fixed, and each one has a regression test in `tests/test_review_fixes.py`:

| # | Finding | Fix |
| --- | --- | --- |
| 1 | A mixed-case or odd old DNS value made rollback and restore fail, leaving DNS broken | Old values are validated before any write. Mixed case is accepted for restore. One bad record no longer blocks the others or the scripts |
| 2 | adb failure or Ctrl-C mid-batch left the batch applied and the scripts stale | Undo the batch, rewrite the scripts and stop with restore instructions. Scripts are also rewritten right after each journal intent |
| 3 | `restore --all` after a new scan restored nothing (it only looked at the latest run) | It searches every run made on this phone |
| 4 | User-installed app names (for example a period tracker) leaked into reports | Only system packages are listed |
| 5 | Custom Private DNS hostnames (which can hold account IDs) survived `share` | Removed from shared copies |
| 6 | Data folder depended on the current folder and could end up in git | Default is `<repo>/reports`, and each data folder gets a `.gitignore` containing `*` |
| 7 | A hand-edited journal could make restore write any setting | Restore checks settings with guard |
| 8 | Failed reads were treated as real state | Failed package lists, settings or role reads now stop the command. Apply refuses when role holders cannot be read |
| 9 | An empty or placeholder serial gave every phone the same identity | Refused |
| 10 | A cut last journal line blocked restore | Moved aside to `journal-damaged-line.txt` |
| 11 | Notification shade or popups could end up in screenshots | The focused window is checked before capture, and the share blur covers the top 10% |
| 12 | The approval does not record the method, and the drill exercises disable only | **Not changed.** Uninstall already needs two explicit flags at apply time and is limited to system packages rated safe. This is a known limit |

During development, the tests also caught two privacy gaps, both fixed:
- Gmail's package name has no "mail" in it, so explicit sensitive package names were added.
- Protected host apps were labelled "ad service active".

## Real phone

No phone was connected (`adb devices` listed none). `doctor` and `scan` were **not** run on a real device. Nothing on any real phone was read or changed. The only effect was that the local adb server was started for that check and then stopped.

## Git

- Repository-only identity: `kc13160 <kc13160@users.noreply.github.com>`.
- `.claude/settings.local.json` contains `{"attribution":{"commit":"","pr":""}}` and is git-ignored. It is not tracked.
- `git log --format=%B | grep -ciE "co-authored|claude|session"` returned **0**: no trailer in any commit message.
- `BUILD.md` is kept out of git through `.git/info/exclude`.

## Publication (section 12b)

All six checks passed before publishing:

1. Tests: 194 passed.
2. `gh api user --jq .login` returned exactly `kc13160`.
3. `gh repo view kc13160/adreceipts` reported "Could not resolve to a Repository", so nothing was overwritten.
4. Tracked files contain no local paths, real emails, tokens, serial numbers, real phone output or real screenshots. The only PNGs are the drawn SIMULATED demo images. Neither `.claude/` nor `reports/` is tracked.
5. The experimental banner is in the README, and the docs make no real-device claim (enforced by `tests/test_docs.py`).
6. `git log` has no trailer.

What was done:

- Published with `gh repo create adreceipts --public --source . --remote origin --push --description "..."`, at https://github.com/kc13160/adreceipts.
- Topics added: android, adb, debloat, ads, adblock, privacy, xiaomi, hyperos, miui, ai-agent, claude-code, no-root, python.
- Push verified from the remote: `git ls-remote origin refs/heads/main` matched local HEAD, and the repository file list matched.
- GitHub Actions run 41489328687: all 11 jobs passed. That covers Python 3.9, 3.10, 3.11, 3.12 and 3.13 on ubuntu-24.04 and windows-latest, plus the standard-library-only job. This confirms Python 3.9.
- No force push. Nothing was published to PyPI, and nothing was posted on social media.

## Finished

- Every file from section 9, with real content. Placeholders appear only in LAUNCH.md.
- All tests pass, and the full simulated run works.
- SIMULATED sample generated and labelled.
- Section 12 review done. Findings 1 to 11 fixed; 12 documented.
- Clean commits with no trailer. No real phone changed.

## Not finished

- **Nothing has been tested on a real phone.** All catalog entries stay `documented`.
- Python 3.9 was not run on this computer. It passed in CI.
- Known limit 12 above.
- The catalog's menu paths come from articles about HyperOS 1 and 2. HyperOS 3 may differ.

## Exact next action for the owner

Follow [TEST_ON_PHONE.md](TEST_ON_PHONE.md) on your Xiaomi phone. Start with step 1 (back up), then step 4:

```text
python adreceipts.py doctor
python adreceipts.py scan
```

Both commands only read. Then fill in the device report (step 10), and use the checklist in [LAUNCH.md](LAUNCH.md) to update the catalog and README with real results before you post the announcement.
