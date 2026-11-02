# Privacy

## What stays on your computer

Everything AdReceipts writes goes to the `reports/` folder of this repository (or the folder set by `--data-dir` / `ADRECEIPTS_HOME`). AdReceipts puts a `.gitignore` inside that folder so git ignores it wherever it is. AdReceipts sends nothing anywhere: no telemetry, no account, no server.

What is stored there:

- package states of the catalog entries, and the names of *system* packages with ad-like names that the catalog does not know (apps you installed yourself are never listed), the settings it reads, the backup, the journal, the plan and the receipts;
- a **hashed** device ID and build fingerprint, made with a random salt kept in `reports/.salt`. The serial number itself is never written;
- phone brand, model and system version (these appear in reports so you know which phone they describe);
- with screenshots only: images of the catalog screens marked safe to capture, and the ad words found on them (never the other text on the screen).

## What can reach your AI provider

If you use AdReceipts through a hosted AI agent, **whatever the agent reads is sent to that agent's provider**: command output, reports it opens, and images if it opens them. The prompt in PROMPT.md asks the agent not to open screenshots unless you ask. AdReceipts never sends anything itself.

## Screenshots

- Off by default. `--screenshots` alone only prints a notice; you must add `--consent`.
- Only screens listed in the catalog with `capture: true`, opened by the tool itself.
- The foreground app and the focused window are read before the capture. If either is not the expected app (for example the notification shade is open), the capture is aborted.
- Never captured: banking, payment, password, messaging, email, gallery, browser, notes, files, downloads and settings screens (both a name check and an explicit list).
- The status bar can show notification icons, and a notification that pops up at the wrong moment can still appear in an image. `share --include-images` blurs the top of each image in the shared copy; the originals stay local. Look at every image before sharing.

## Sharing

`python adreceipts.py share` writes a sanitized copy of the reports: device hashes, account names, email addresses, long numbers (such as IMEI or serial-like strings), local paths and custom Private DNS hostnames (which can contain a personal account ID) are removed, and images are left out. Add `--include-images` only after looking at every image; the status bar is blurred, which needs the optional Pillow package. Read the copy once more before you post it.

## Private DNS

If you choose Private DNS filtering, the provider you pick sees every domain name your phone looks up, for every app. Choose a provider you trust, or none.
