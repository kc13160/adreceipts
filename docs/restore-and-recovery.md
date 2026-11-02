# Restore and recovery

## Undo with AdReceipts

```text
python adreceipts.py restore --all          # every change recorded in the latest run
python adreceipts.py restore --batch 2      # one batch
python adreceipts.py restore --all --run 20261102-174053   # a specific run
```

`restore` reads the journals of every run made on this phone (or only `--run ID`) and reverses only what they recorded, newest first. A later `scan` starts a new run but does not hide earlier changes from `restore --all`. It never turns on something that was already off before AdReceipts, and it never touches what you changed by hand. Each undo is read back. Then run `python adreceipts.py recheck`.

Restore works after a system update. It refuses a different phone.

## Undo without Python

Each run folder has two scripts, regenerated after every change:

- `restore-standalone.cmd` for Windows: double-click it, or run it in a terminal.
- `restore-standalone.sh` for macOS and Linux: `sh restore-standalone.sh`.

They contain only the adb commands that reverse the journal. They use `adb` from your PATH, or the path in the `ADB` environment variable. Connect only the phone the run was made for.

## Undo by hand on the phone

If a computer is not available:

1. Open **Settings > Apps** (on Xiaomi: **Settings > Apps > Manage apps**).
2. Open the menu and choose to show system apps.
3. Find the app (the plan and receipts show its name and package name), open it, and tap **Enable**.

For Private DNS: **Settings > Connection & sharing** (or **Network & internet**) **> Private DNS**, then choose **Automatic** or **Off**, as it was before.

## If the phone misbehaves

- **Calls, SMS or notifications stop working:** run `restore --all`, then restart the phone.
- **The phone is stuck or restarts in a loop:** this should not happen with `disable-user`, which keeps the app installed. Turn the phone off and on. If USB debugging still works, run `restore --all` or the standalone script. If not, use the manual steps above once the phone starts.
- **An app came back after a system update:** that is common. `recheck` shows it. Nothing is reapplied automatically; run scan, backup, drill and plan again if you want it off.
- **AdReceipts says the files belong to another phone or system version:** start a new run with `scan`. Restore still works for the same phone after an update.

## What a restore cannot do

- It cannot undo changes made by other tools or by hand.
- It cannot bring back a package that a system update removed.
- `--method uninstall` can only be undone while the package is still part of the system image, which is why AdReceipts refuses it for anything else.
