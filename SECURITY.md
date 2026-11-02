# Security and threat model

AdReceipts changes system settings on a phone over USB. This page lists what could go wrong and what the code does about it.

## Reporting a problem

Please report security or safety problems through GitHub's private vulnerability reporting on this repository ("Security" tab > "Report a vulnerability"). Do not include personal data from your phone.

## What could damage a phone, and the protections

| Risk | Protection in code |
| --- | --- |
| Turning off something the phone needs (phone, SMS, home screen, keyboard, WebView, updates, security) | `catalog/protected.txt` (exact names and prefixes), a runtime check of role holders (home, dialer, SMS, browser, assistant, keyboard, WebView, device admin, accessibility), and refusal of every package not in the catalog |
| Breaking banking, payment or login apps | Names containing bank, wallet, pay, auth or 2fa are refused unless the catalog rates that exact package safe |
| A change that cannot be undone | `pm disable-user` by default. The uninstall method needs two flags, only for system-image packages rated safe, and is reversed with `cmd package install-existing` |
| Changing things before undo is proven | `apply --execute` refuses without a backup and a passed drill for the same phone, system build and run. There is no skip flag |
| A bad change spreading | Batches of at most 5, risky items alone. Read-back after each change, health checks after each batch, automatic undo of that batch, and the run stops |
| Losing track of what changed | The journal is written before each change. `restore` reverses only journal entries; a standalone script does the same without Python |
| Command injection | No local shell. adb calls are argument lists; every argument must match a strict pattern because `adb shell` joins arguments on the phone. Package, setting and hostname values are validated again |
| A read-only command writing by mistake | Read-only commands open adb at the `read` level; write commands are refused by the adb layer itself |
| Applying files made for another phone | Plans, backups and drills carry a hashed device ID and build fingerprint; a mismatch stops the run |
| Managed or work phones | A work profile, device owner or profile owner stops every command |
| Manufacturer blocks | A blocked disable is reported; the method is never switched automatically, and a new approval is required |
| DNS cutting the phone off | The old value is saved, lookups are tested, and the old value is put back on failure |

## What could leak private data, and the protections

See [PRIVACY.md](PRIVACY.md). In short: no telemetry, reports stay local and are git-ignored, serial numbers are hashed with a local random salt, screenshots are off by default and limited to catalog screens marked safe, the foreground app is checked before each capture, and `share` removes IDs, accounts, emails, long numbers and local paths, and leaves images out by default.

## Out of scope

Root, bootloaders, flashing, custom ROMs, DRM or licence bypass, wireless ADB, managed phones.

## Known limits

- The catalog comes from public sources. Nothing in it has been tested on a real device yet.
- Package names and menus change between versions and regions. A safe entry on one build may behave differently on another.
- A health check cannot prove every feature works. That is why `verify` asks you to check calls, SMS, notifications and payment apps yourself.
