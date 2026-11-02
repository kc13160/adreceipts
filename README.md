# AdReceipts

**Your AI agent finds the ads built into your Android phone, removes them, and shows the before/after proof. No root. Every change can be undone.**

> **Experimental. Not yet tested on a real device. Use at your own risk and back up your data first.**

Designed for Android. Tested only on the models listed in the catalog.

## What you see

1. **A scan that changes nothing.** A plain-language page listing the places where your phone shows its own ads (lock screen, Security and Cleaner apps, Themes, Downloads, Music, Video, Browser, app folders...), what was found, and how each one is turned off. You can stop there.
2. **A plan you approve.** Each change comes with its risk, its side effects and its public source. Nothing is pre-selected unless it has been tested on a real device.
3. **Receipts.** A before/after page for each screen, with the exact change made. A receipt only says what was observed: if no ad was seen before, the result is "not proven", never "removed".
4. **An undo for everything.** Every change is written to a journal *before* it is made. `restore` reverses exactly what the journal recorded, and a standalone script does the same without Python.

## The safety promise

- **Read first.** `scan` only reads. Screenshots are off unless you agree.
- **Undo is proven before cleanup.** `drill` disables one harmless package, reads the state back, turns it on again and reads it back. `apply --execute` refuses to run without a passed drill for this phone and this run. There is no flag to skip it.
- **Nothing happens without your approval**, and `apply` is a dry run unless you add `--execute`.
- **Guard checks every package before any write.** Protected system parts, banking, payment and login apps, and whatever holds the home, phone, SMS, browser, assistant, keyboard, WebView, device admin or accessibility role right now are refused. One refusal stops the whole batch before anything is written.
- **Small batches with health checks.** At most 5 packages per batch, risky ones alone. After each batch: read-back, phone reachable, fully started, home screen and System UI running, phone and SMS apps enabled. Any problem undoes that batch and stops.
- **No root, no flashing, no wireless ADB, no telemetry.** Work profiles and managed phones stop the run.

What it does **not** promise: an ad-free internet, removing ads inside other apps or YouTube, or any speed, battery or memory gain. A DNS filter blocks some ad domains, not all ads. A screen without an ad at one moment does not prove the ad is gone for good.

## SIMULATED sample

> **SIMULATED.** The sample below was produced with a fake phone (`tests/fake_adb.py`) by `python demo/make_demo.py`. The images are drawn by that script. It is not a real device result.

- [demo/sample/scan.html](demo/sample/scan.html): the read-only scan
- [demo/sample/plan.html](demo/sample/plan.html): the plan, with risks and the switches to turn off by hand
- [demo/sample/receipts.html](demo/sample/receipts.html): before/after receipts

Terminal output of `scan` on the fake phone (SIMULATED):

```text
Scan finished. Nothing was changed on the phone.
Phone: Xiaomi SIMULATED-PHONE, Android 16, system OS3.0.301.0.SIMULATED
Ad or tracking services switched on: 6
  - com.mi.globalminusscreen (App Vault (panel left of the home screen))
  - com.miui.analytics (Xiaomi analytics (usage data sent to Xiaomi))
  - com.miui.android.fashiongallery (Wallpaper Carousel (lock screen images))
  - com.miui.daemon (Xiaomi system daemon (collects usage data))
  - com.miui.hybrid (Quick Apps (instant mini apps))
  - com.miui.msa.global (Xiaomi system ads service (msa))
Unrecognized ad-like packages (reported only): 1
Report: reports/20261102-175126/scan.html
Run: 20261102-175126

You can stop here. To continue: python adreceipts.py backup
```

## Quick start

You need: Python 3.9 or newer, [Android SDK platform-tools](https://developer.android.com/tools/releases/platform-tools) (for `adb`), a USB cable, and USB debugging turned on.

**With an AI agent (recommended):** clone this repository, open the folder in your coding agent, and paste the content of [PROMPT.md](PROMPT.md). The agent walks you through each step and asks for your approval.

**By hand:**

```text
git clone https://github.com/kc13160/adreceipts
cd adreceipts
python adreceipts.py doctor        # adb, authorization, one phone, no work profile
python adreceipts.py scan          # read-only; you can stop here
python adreceipts.py backup        # saves state, writes the standalone restore scripts
python adreceipts.py drill         # proves undo on this phone
python adreceipts.py plan          # lists choices with risks
python adreceipts.py plan --select pkg:com.miui.msa.global --approve
python adreceipts.py apply         # dry run
python adreceipts.py apply --execute
python adreceipts.py verify        # health checks and a checklist for calls, SMS, notifications, payments
python adreceipts.py receipts      # before/after page
python adreceipts.py restore --all # undo everything AdReceipts did
python adreceipts.py recheck       # after a system update: what came back
python adreceipts.py share         # sanitized copy, without images by default
```

Every command has `--help`, accepts `--adb PATH` (or the `ADRECEIPTS_ADB` variable) and returns a non-zero code on failure. Reports stay on your computer in `reports/`, which git ignores.

Optional: Private DNS ad filtering with `plan --dns adguard`, `--dns mullvad` or `--dns custom --dns-host HOST`. The provider sees the domain names your phone looks up. The old setting is saved, name lookups are tested right after, and the old setting is put back if they fail.

## Comparison of approach

Checked on 2026-11-02 from each project's public README. These are differences of approach, not of quality.

| | AdReceipts | [Universal Android Debloater Next Generation](https://github.com/Universal-Debloater-Alliance/universal-android-debloater-next-generation) | [CleanYourTV](https://github.com/Gathin23/cleanyourtv) |
| --- | --- | --- | --- |
| Device | Android phones | Android devices | Android TV and Google TV |
| Interface | Command line driven by your AI agent | Desktop app | Prompt for a coding assistant |
| Focus | Ads built into the phone, with before/after receipts | Removing unnecessary system apps for privacy and efficiency | Disabling TV bloat and ads, plus a clean launcher |
| Connection | USB only | ADB | Wi-Fi |

## Contributing

The catalog lists **where ads appear and how to turn them off**, with a proof level for each entry. You can help without writing code: open an [ad location issue](.github/ISSUE_TEMPLATE/ad_surface.yml) or a [device report](.github/ISSUE_TEMPLATE/device_report.yml). See [CONTRIBUTING.md](CONTRIBUTING.md).

## More

- [docs/how-it-works.md](docs/how-it-works.md)
- [docs/restore-and-recovery.md](docs/restore-and-recovery.md)
- [docs/faq.md](docs/faq.md)
- [PRIVACY.md](PRIVACY.md) and [SECURITY.md](SECURITY.md)

MIT licence. See [NOTICE.md](NOTICE.md) for credits.
