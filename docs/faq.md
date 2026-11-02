# FAQ

**Does it need root?**
No. It uses `adb` over USB with USB debugging on, like the Settings app would.

**Which phones does it work on?**
Designed for Android. Tested only on the models listed in the catalog, and none is listed as tested yet. The scan runs generic checks on Android phones reachable over USB; detailed ad locations exist so far for Xiaomi, Redmi and Poco phones with HyperOS, from public sources.

**Will I never see an ad again?**
No promise of that. AdReceipts deals with ads built into the phone's own apps and screens. Ads inside other apps, websites or YouTube are not its job. Updates can bring things back; `recheck` shows what came back.

**Will my phone be faster or the battery last longer?**
AdReceipts makes no such claim.

**What exactly is changed?**
Only what you approved in the plan, listed with the exact command. Each change is written to a journal before it happens.

**Can I just look?**
Yes. `doctor` and `scan` change nothing. You can stop after the scan.

**Why the "drill"?**
To prove on your phone that undo works before anything real is changed. Some manufacturers block certain changes; better to learn that on a harmless package.

**Why are so many locations "not checked"?**
Most ad switches are inside app menus that cannot be read over USB without opening the screen. Screen evidence is off by default. With `--screenshots --consent`, AdReceipts opens a few screens marked safe to capture and looks for ad words.

**Why is nothing pre-selected in the plan?**
Only entries that are rated safe *and* tested on a real device are pre-selected. Today the catalog only has documented entries, so you choose each item yourself.

**What is "not proven" in the receipts?**
No ad was seen on that screen before the change, so a "before/after" cannot prove anything there.

**Does AdReceipts send my data anywhere?**
No. Reports stay in `reports/`. But your AI agent's provider receives what the agent reads. See [PRIVACY.md](../PRIVACY.md).

**Private DNS: should I use it?**
It is optional and off by default. It blocks some ad domains for all apps, but the provider sees the domain names your phone looks up, and it can block things you want. If lookups fail after setting it, AdReceipts puts the old setting back.

**My phone has a work profile / is managed by my employer.**
AdReceipts stops. Ask whoever manages the phone.

**How do I undo everything?**
`python adreceipts.py restore --all`, or the standalone script in the run folder. See [restore-and-recovery.md](restore-and-recovery.md).
