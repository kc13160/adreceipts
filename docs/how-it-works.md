# How AdReceipts works

AdReceipts is a small Python program (standard library only) that talks to your phone through `adb` over a USB cable. Your AI agent runs it for you and explains each step, but every safety rule lives in the code.

## The flow

```text
doctor -> scan -> backup -> drill -> plan -> (approve) -> apply -> verify -> receipts
                                                          \-> restore, recheck, share at any time
```

| Command | Changes the phone? | What it does |
| --- | --- | --- |
| `doctor` | no | Checks adb, that exactly one phone is connected and authorized, and that it has no work profile or device management |
| `scan` | no | Reads package states and settings, matches them with the catalog, writes `scan.md` and `scan.html` |
| `backup` | no | Saves the state of every catalog package and the DNS settings; writes the standalone restore scripts |
| `drill` | yes, then undone | Disables one harmless package, reads it back, enables it, reads it back; writes `drill.json` |
| `plan` | no | Lists what can be changed, with risk, side effects, proof level and source; records your selection and approval |
| `apply` | only with `--execute` | Runs the approved plan in batches, with read-back, health checks and automatic undo |
| `verify` | no | Health checks, plus a checklist you confirm by hand |
| `receipts` | no (screens are opened only with consent) | Before/after page |
| `restore` | yes | Reverses journal entries, newest first |
| `recheck` | no | Compares the phone with the last scan, for example after a system update |
| `share` | no (offline) | Sanitized copy of the reports |

## Where ads come from on a phone

- **Ad services**: system packages that fetch and show ads or collect usage data (for example Xiaomi's `msa`).
- **Ad switches**: settings inside system apps (Security, Cleaner, Downloads, Themes, Music, Video, Browser, app drawer, folders). Most of them can only be changed by hand in the app's menus, so the plan lists the exact steps.
- **Ad apps**: apps whose main job is to show content with promotions (lock screen wallpaper carousel, App Vault).

## Labels

A scan never gives a score or a "clean" verdict. Each location gets one or more of:

| Label | Meaning |
| --- | --- |
| `ad seen` | Ad words were found on that screen (screenshots on) |
| `ad setting on` | A readable setting says the ad switch is on |
| `ad service active` | A package that serves ads or tracking is enabled |
| `not seen at scan time` | The screen was checked and no ad words were found at that moment, or the service is off |
| `not checked` | No screen evidence was collected for this location |

Receipts compare before and after. A location with no ad seen before is `not proven`, never "removed".

## Runs and files

Each `scan` starts a run: a folder `reports/<date-time>/`. Later commands use the latest run (or `--run ID`). A run holds `run.json`, `scan.*`, `backup.json`, `drill.json`, `plan.*`, `journal.jsonl`, `apply.json`, `verify.json`, `receipts.*`, `recheck-*`, the standalone restore scripts and, with consent, `screens/`.

Backup, drill and approval are tied to a hashed device ID and a hashed build fingerprint. After a system update, start a new run.

## The catalog

`catalog/<brand>/<family>.yml`, checked against `catalog/schema.json`. Each entry has a public source and a proof level: `documented` (public source), `reported` (a contributor says it works) or `tested` (verified on a real device with a linked report). Only `safe` and `tested` entries are pre-selected. Today every entry is `documented`.

`catalog/protected.txt` lists packages that are never touched. At run time, guard also protects whatever currently holds the home, dialer, SMS, browser, assistant, keyboard, WebView, device admin and accessibility roles.

## Methods

- Default: `pm disable-user --user 0 <package>`, undone with `pm enable --user 0 <package>`.
- Advanced: `pm uninstall -k --user 0 <package>` with `--method uninstall --i-understand-uninstall`, only for system-image packages rated safe, undone with `cmd package install-existing --user 0 <package>`.
- If the phone blocks a disable, AdReceipts stops, undoes that batch and asks for a new approval. It never switches method by itself.
- Private DNS: `settings put global private_dns_specifier <host>` and `private_dns_mode hostname`, then a name lookup test, with rollback on failure.
