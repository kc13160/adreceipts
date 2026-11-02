# Contributing to AdReceipts

Thank you. The most useful help is knowledge about **where ads appear on a phone and how to turn them off**, backed by a source or a device report.

## Without writing code

- **Report an ad location:** open an issue with the "Ad location" form. Say which phone family and system version, where the ad appears, and the exact menu path that turns it off. A screenshot helps, but only after you run `python adreceipts.py share` and check the image yourself: no account names, no notifications, no personal content.
- **Report a device test:** open an issue with the "Device report" form after you tried AdReceipts on your phone. Say what worked, what did not, and what you checked afterwards (calls, SMS, notifications, payment apps). Do not paste serial numbers, IMEI, account names or full logs.

A maintainer turns these reports into catalog entries.

## Adding or changing a catalog entry

Catalog files live in `catalog/<brand>/<family>.yml` and follow `catalog/schema.json`. Check them with:

```text
python adreceipts.py catalog-check
```

Rules:

- Every entry needs a public `source` URL (https). If you cannot source it, leave it out.
- New entries start as `proof: "documented"` (public source, no device report) or `"reported"` (a contributor says it works).
- `proof: "tested"` needs a `report`: a link to a device report (https URL, or a file in `catalog/reports/`). The tests fail otherwise.
- Use plain words in `name`, `role` and `side_effects`: the people reading them may be helping a parent.
- `risk` is one of `safe`, `prudent`, `advanced`, `forbidden`. When unsure, choose the more careful level. Only entries that are both `safe` and `tested` are pre-selected in a plan.
- Packages in `catalog/protected.txt` must be rated `forbidden`.
- Prefer a settings path over disabling an app that hosts other features (for example the Xiaomi Security app).
- Write version numbers and words like yes/no in quotes. The catalog reader is strict on purpose.
- Do not copy lists from other projects unless their licence clearly allows it, and credit them in NOTICE.md.

## Adding a device report

Copy the device report template into `catalog/reports/<brand>-<model>-<date>.md`, remove anything personal, and link it from the entries you tested. Keep it short: phone family, system version, what was changed, what was checked, what was restored.

## Changing the code

```text
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt      # Windows: .venv\Scripts\pip
python -m pytest
```

- The core uses the Python standard library only. Python 3.9 to 3.13, Windows, macOS and Linux.
- Read [CLAUDE.md](CLAUDE.md): adb calls are argument lists, guard checks every write, the journal is written before each change, and nothing may skip the drill.
- Add a test for every safety behaviour you touch. Use `tests/fake_adb.py`; never a real phone in tests.
- `python demo/make_demo.py` regenerates the SIMULATED sample.
