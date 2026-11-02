# Decisions made during the autonomous build

The owner was away. Each time something was unclear, the safest reasonable option was chosen and written down here.

## Scope and wording

1. **No real-device claims anywhere.** Every catalog entry is `documented`. The README carries the experimental banner. The owner's phone (HyperOS 3.0.301.0, Android 16) is not recorded as tested; the scan says plainly that HyperOS 3 is not among the versions the sources describe.
2. **`system_versions` for Xiaomi lists only "HyperOS 1" and "HyperOS 2"**, because the sources describe those. The file still matches any phone with a HyperOS property, so HyperOS 3 users get the entries, with that warning.
3. **Left out of the catalog: "Security scan before installation".** One source lists it as an ad location, but turning it off removes a malware check. Leaving a protection on is the safer default.
4. **Left out: File Manager recommendations** (the source says the switch no longer exists on HyperOS) and any entry without a working public source. Home-screen folders are included with an honest "the exact control varies" note, because the only source names the place but not the exact path.
5. **Host apps (Security, Downloads) are listed as `forbidden` packages** so the scan explains them and the plan refuses them, with the settings path offered instead. The Xiaomi Security app is also in `protected.txt`.
6. **Apps like Music, Video, Browser are offered only as `prudent`** with the side effect "the whole app stops"; their own ad switches are listed as manual steps first. Themes is `advanced` (disabling breaks theme changes).
7. **UAD-ng's list (GPL-3.0) is cited as a source URL but nothing was copied.** CleanYourTV's licence was unclear when checked, so it is credited as inspiration only.

## Safety behaviour

8. **Uninstall method allowed only for `safe` entries**, stricter than the brief's "never for prudent". `advanced` entries are refused too.
9. **Any blocked, failed or unhealthy batch is undone and the run stops**, including a manufacturer block. After a block, the plan approval is cleared so a new approval is required, and the method is never switched.
10. **Every item of the whole plan goes through guard before the first write** (not only the current batch), and again before each batch with fresh role holders.
11. **Read-only commands are enforced in the adb layer**, not just by convention: commands open adb at a `read`, `screen` or `write` level, and unknown commands count as writes.
12. **Every `adb shell` argument must match a strict character pattern**, because `adb shell` joins arguments into one string on the phone.
13. **Device identity = salted hash of the adb serial + salted hash of `ro.build.fingerprint`.** Backup, drill and approval require both to match, so a system update requires a new run. `restore` and `receipts` only require the same phone, so undo still works after an update.
14. **The standalone restore scripts are generated from the journal** (rewritten after every change). At backup time they contain "nothing to restore yet". This follows "reverse only what the journal recorded".
15. **The drill must come after the backup** in the same run; apply needs backup, drill and approval from the same run.
16. **Health checks:** adb `get-state` with retries, `sys.boot_completed`, a running home-screen process, System UI running with the same PID as before the batch (a new PID is treated as a crash), and the phone and SMS role holders still enabled.
17. **DNS lookup test uses `ping -c 1` against `connectivitycheck.gstatic.com`**: a resolved address counts as success even if the ping itself gets no reply. Ad filters do not block that domain.
18. **"Unknown packages"** are packages with ad-like name parts (ads, analytics, tracker, promo, msa...) that are not in the catalog. They are reported only.

## Screenshots and privacy

19. **Consent is a second flag:** `--screenshots` alone prints the notice and exits; `--screenshots --consent` proceeds. An agent cannot click a dialog, so PROMPT.md tells it to read the notice to the user and ask first.
20. **Screen capture is allow-listed in the catalog** (`capture: true`), plus a deny list by name parts and exact package names (messaging, email, gallery, browser, settings, files, notes...). Only Security and Themes are marked capturable today.
21. **UI dumps and screenshots are streamed with `exec-out`** (`uiautomator dump /dev/tty`, `screencap -p`), so nothing is written on the phone. Only matched ad words are kept from the UI text.
22. **`scan` opens no screen without consent**, so the default scan sends no `am start`, `input` or capture command.
23. **`share --include-images` needs Pillow** to blur the status bar; without it, it refuses rather than share unblurred images.

## Engineering

24. **YAML without PyYAML:** a small strict YAML reader (`adreceipts/yamlite.py`) and a small JSON Schema checker keep the core dependency-free. Tests compare both with PyYAML and jsonschema when installed.
25. **A `--adb` path ending in `.py` is run with the current Python.** This lets tests and the demo use `tests/fake_adb.py` on Windows without a wrapper.
26. **Extra command `catalog-check`** for contributors and CI.
27. **`verify` records confirmations with `--confirmed calls sms notifications payments`** and problems with `--problem`, since an agent relays the user's answers.
28. **Reports live in `./reports` by default** (or `--data-dir` / `ADRECEIPTS_HOME`), git-ignored. Runs are named by local date and time.
29. **BUILD.md is kept out of git** (listed in `.git/info/exclude`): it is the build brief, not part of the product.
30. **Line endings:** `.gitattributes` stores text with LF; `.cmd` files with CRLF.

## After the fresh-eyes review (section 12)

31. **Old values must be restorable before a change.** If the current Private DNS value or a catalog setting holds characters that cannot be sent back safely, the change is refused before any write. Mixed-case hostnames are accepted for restore.
32. **adb failure or Ctrl-C in the middle of a batch** now tries to undo that batch, rewrites the restore scripts, and stops with restore instructions. The standalone scripts are also rewritten right after each journal intent, before the command is sent.
33. **`restore --all` looks through every run made on this phone** (newest first) unless `--run` is given, because each `scan` starts a new run. `--batch ID` uses the newest run that has that batch.
34. **Restore refuses settings that guard would refuse**, so a hand-edited journal cannot make it write arbitrary settings.
35. **Failed reads stop the command instead of guessing:** a failed or incomplete package list, a failed `settings get`, or unreadable role holders (apply refuses; Android 10+ is needed for changes). A phone without a unique serial (empty or placeholder) is refused, so two phones cannot share an identity.
36. **Only system packages appear in the "unrecognized ad-like packages" list**: user-installed app names can be private.
37. **`share` removes custom Private DNS hostnames**; catalog providers are kept.
38. **The default data folder is `<repository>/reports`** whatever the current folder, and every data folder gets a `.gitignore` containing `*`.
39. **A cut last journal line** (crash while writing) is moved to `journal-damaged-line.txt` instead of blocking restore.
40. **Captures also check the focused window**, and share blurs the top 10% of images instead of 6%.
41. **Not changed: the approval does not record the method, and the drill only exercises disable/enable.** The uninstall method already needs two explicit flags at apply time and is limited to system packages rated safe. Recorded as a known limit in REPORT.md.
