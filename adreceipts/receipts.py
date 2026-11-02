"""receipts: the before/after proof page.

A receipt says only what was observed. A location with no ad seen before stays
"not proven", never "removed".
"""

from __future__ import annotations

from . import device, evidence, report, screen
from .errors import AdReceiptsError
from .journal import Journal
from .store import now_iso, read_json, require_same_device, write_json

NOT_PROVEN = "not proven"
NOT_SEEN_AFTER = "ad not seen after change"
STILL_SEEN = "still seen"


def outcome(before_ev, after_ev):
    seen_before = bool(before_ev and before_ev.get("checked") and before_ev.get("ad_seen"))
    if not seen_before:
        return NOT_PROVEN
    if not (after_ev and after_ev.get("checked")):
        return evidence.NOT_CHECKED
    return STILL_SEEN if after_ev.get("ad_seen") else NOT_SEEN_AFTER


def summary(ev, labels):
    if ev and ev.get("checked"):
        return "ad words seen: %s" % ", ".join(ev["ad_words"]) if ev.get("ad_seen") else "screen checked, no ad words found"
    return ", ".join(labels) if labels else "not checked"


def changes_by_target(journal):
    out = {}
    for c in journal.changes().values():
        if c["batch"] == "drill":
            continue
        out.setdefault(c["target"], []).append(c)
    return out


def describe_change(c):
    verb = {"disable": "disabled", "uninstall": "uninstalled for user 0", "setting": "set", "dns": "Private DNS set to"}[c["op"]]
    state = {"done": "", "undone": " (then undone)", "restored": " (then restored)", "failed": " (failed)",
             "blocked": " (blocked by the phone)", "intent": " (result unknown)"}.get(c["phase"], "")
    return "batch %s: %s %s%s" % (c["batch"], verb, c["target"], state)


def run(app):
    args = app.args
    if args.screenshots and not args.consent:
        app.say(screen.CONSENT_TEXT)
        return 2
    adb = app.connect("screen" if args.screenshots else "read")
    props, dev = device.identity(adb, app.home)
    run_id, run_dir = app.run()
    run_info = read_json(run_dir / "run.json") or {}
    require_same_device(run_info.get("device"), dev, "run %s" % run_id, check_build=False)
    scan = read_json(run_dir / "scan.json")
    if not scan:
        raise AdReceiptsError("No scan in this run.", hint="Run: python adreceipts.py scan")
    cat = app.catalog(props)
    screens = evidence.capture_all(adb, cat, run_dir, "after", app.sleep) if args.screenshots else {}
    after = evidence.collect(adb, cat, screens)
    before = scan["evidence"]
    journal = Journal(run_dir)
    by_target = changes_by_target(journal)
    updated = before is not None and run_info.get("device", {}).get("build_hash") != dev.get("build_hash")

    surface_blocks, rec_surfaces, table_rows = [], {}, []
    run_changes = [describe_change(c) for cs in by_target.values() for c in cs if c["phase"] == "done"]
    for sid, s in cat.surfaces.items():
        b_info = before["surfaces"].get(sid, {})
        a_info = after["surfaces"].get(sid, {})
        if not b_info.get("present", True) and not a_info.get("present", True):
            continue
        b_ev = before.get("screens", {}).get(sid)
        a_ev = after.get("screens", {}).get(sid)
        result = outcome(b_ev, a_ev)
        related = cat.packages_for_surface(sid)
        st = s["turn_off"].get("setting")
        targets = related + (["%s/%s" % (st["namespace"], st["key"])] if st else [])
        exact = [describe_change(c) for t in targets for c in by_target.get(t, [])]
        rec_surfaces[sid] = {"before": b_info.get("labels", []), "after": a_info.get("labels", []), "outcome": result,
                             "changes": exact}
        how = (" ".join(s["turn_off"].get("steps", [])) if s["turn_off"]["method"] == "manual"
               else "through: %s" % s["turn_off"]["method"])
        if exact:
            change_text = "; ".join(exact)
        elif run_changes:
            change_text = "none aimed at this location. Changes made in this run: " + "; ".join(run_changes)
        else:
            change_text = "none made by AdReceipts"
        has_screen = any(e and (e.get("checked") or e.get("image")) for e in (b_ev, a_ev))
        if has_screen:
            surface_blocks.append({"pair": {
                "caption": "%s - result: %s" % (s["name"], result),
                "before": {"image": (b_ev or {}).get("image"), "summary": summary(b_ev, b_info.get("labels", []))},
                "after": {"image": (a_ev or {}).get("image"), "summary": summary(a_ev, a_info.get("labels", []))},
            }})
            surface_blocks.append({"ul": ["Exact change: %s" % change_text, "How to turn it off by hand: %s" % how]})
        else:
            table_rows.append([s["name"], {"badges": [result]}, {"badges": b_info.get("labels", [])},
                               {"badges": a_info.get("labels", [])}, change_text])

    pkg_rows = []
    names = sorted(set(before["packages"]) | set(after["packages"]))
    for n in names:
        b = before["packages"].get(n, {}).get("state", "absent")
        a = after["packages"].get(n, {}).get("state", "absent")
        ch = "; ".join(describe_change(c) for c in by_target.get(n, [])) or "none"
        pkg_rows.append([{"code": n}, b, a, ch])
    other = [describe_change(c) for t, cs in by_target.items() for c in cs if c["op"] == "dns"]

    sections = [
        {"h": "Summary", "blocks": [
            {"p": "Phone family: %s. Before: scan of %s. After: %s." % (report.device_line(dev), scan["time"], now_iso())},
            {"note": "A receipt says only what was observed. A location where no ad was seen before is 'not proven', "
                     "never 'removed'. A screen without an ad at one moment does not prove the ad is gone for good."},
        ] + ([{"note": "The system version changed since the scan (an update). Run recheck."}] if updated else [])},
        {"h": "How to read the results", "blocks": [{"table": {"head": ["Result", "Meaning"], "rows": [
            [{"badges": [NOT_SEEN_AFTER]}, "An ad was seen before; after the change no ad words were found on that screen."],
            [{"badges": [STILL_SEEN]}, "An ad was seen before and is still seen."],
            [{"badges": [NOT_PROVEN]}, "No ad was seen before (or the screen was not checked), so nothing can be proven."],
            [{"badges": [evidence.NOT_CHECKED]}, "The screen was not checked after the change."],
        ]}}]},
        {"h": "Screens checked before and after", "blocks": surface_blocks or [
            {"p": "No screen was checked. Use --screenshots --consent on scan and receipts to collect screen evidence."}]},
        {"h": "Other ad locations (no screen evidence)", "blocks": [{"table": {
            "head": ["Location", "Result", "Before", "After", "Exact change"], "rows": table_rows}}]},
        {"h": "Packages, before and after", "blocks": [{"table": {
            "head": ["Package", "Before", "After", "Change made by AdReceipts"], "rows": pkg_rows}}]},
    ]
    if other:
        sections.append({"h": "Other changes", "blocks": [{"ul": other}]})
    sections.append({"h": "Undo", "blocks": [{"ul": [
        "Undo everything: python adreceipts.py restore --all",
        "Undo one batch: python adreceipts.py restore --batch <ID>",
        "Without Python: run restore-standalone.cmd (Windows) or restore-standalone.sh in this folder.",
    ]}]})
    sections.append({"h": "What this does not prove", "blocks": [{"ul": report.LIMITS}]})
    doc = {"title": "AdReceipts receipts", "subtitle": "%s - %s" % (report.device_line(dev), now_iso()),
           "simulated": dev.get("simulated"), "sections": sections}
    write_json(run_dir / "receipts.json", {"time": now_iso(), "surfaces": rec_surfaces, "after": after})
    path = report.write(doc, run_dir, "receipts", template="receipts.html")
    app.say("Receipts written (nothing on the phone was changed): %s" % path)
    counts = {}
    for r in rec_surfaces.values():
        counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
    for k in sorted(counts):
        app.say("  %s: %d" % (k, counts[k]))
    app.say("", "Before sharing anything, run: python adreceipts.py share")
    return 0
