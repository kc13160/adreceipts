# Changelog

## 0.1.0 - 2026-11-02

First public version. Experimental: not yet tested on a real device.

- Commands: doctor, scan, backup, drill, plan, apply, verify, receipts, restore, recheck, share, catalog-check.
- Read-only scan with honest labels (ad seen, ad setting on, ad service active, not seen at scan time, not checked).
- Before/after receipts; optional screenshots with consent and foreground check.
- Undo drill required before any change; journal written before each change; standalone restore scripts.
- guard: protected list, runtime role protection, risky name patterns, strict name validation.
- Batches of at most 5 with read-back, health checks and automatic undo.
- Optional Private DNS filtering with lookup test and rollback.
- Catalog: generic Android checks and Xiaomi/Redmi/Poco HyperOS ad locations from public sources, all "documented".
- SIMULATED demo built with a fake adb.
