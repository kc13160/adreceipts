# Launch kit

Placeholders in `[BRACKETS]` must be replaced with real results from the phone test in TEST_ON_PHONE.md. Do not post before that test is done.

## GitHub description

```text
Your AI agent finds the ads built into your Android phone, removes them, and shows the before/after proof. No root. Every change can be undone.
```

## Suggested topics

```text
android adb debloat ads adblock privacy xiaomi hyperos miui ai-agent claude-code no-root python
```

## Draft post for X or Threads (English)

```text
My [PHONE MODEL] shows ads inside its own system apps. So I built AdReceipts: your AI agent scans the phone (read-only), proves undo works, then turns off the ad sources you approve, and gives you before/after receipts.

On my phone: [RESULT]

No root. Every change is journaled and can be undone. Experimental, tested only on the models in the catalog.

https://github.com/kc13160/adreceipts
```

Rules for the post: only results you saw on your own phone, no percentages, no speed or battery claims, no "ad-free" promise.

## 30-second before/after video script

| Time | Picture | Voice or caption |
| --- | --- | --- |
| 0-4 s | The phone's [SCREEN WITH AN AD], ad circled | "This ad is built into my phone." |
| 4-9 s | Terminal: agent runs `scan` | "My AI agent scans the phone first. Nothing is changed." |
| 9-14 s | `drill` output: "Drill passed" | "It proves undo works before touching anything." |
| 14-19 s | `plan` with risks, user types yes | "I approve each change." |
| 19-25 s | `receipts.html`: before/after pair | "[RESULT]. Every change has a receipt." |
| 25-30 s | `restore --all` command on screen | "And one command undoes it all. Link below." |

Blur the status bar and anything personal before recording. Use `share` for any report you show.

## After the phone test: update checklist

- [ ] Fill in the device report from `catalog/reports/TEMPLATE.md`, without serial, IMEI, account names or phone number.
- [ ] For each entry you changed and undid successfully, set `proof: "tested"` and `report: "catalog/reports/<file>.md"`. Run `python adreceipts.py catalog-check` and `python -m pytest`.
- [ ] If HyperOS [VERSION] behaved as described, add it to `system_versions` in `catalog/xiaomi/hyperos.yml`.
- [ ] Fix any menu path that differed on your phone, keeping the source link, and note the difference.
- [ ] In README.md, replace the status banner with: "Tested on [MODEL] with [SYSTEM VERSION]. Other phones: experimental." Keep "Designed for Android. Tested only on the models listed in the catalog."
- [ ] Add a short "Real results" section with what you observed, labelled with the model and date. No percentages, no gains.
- [ ] Replace the SIMULATED sample only with a `share` copy you reviewed, and keep the SIMULATED one labelled as such if you keep it.
- [ ] Check `git status` and `git diff` for private data before every commit.
