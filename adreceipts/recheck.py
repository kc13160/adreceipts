"""recheck: after an update, show what came back or changed. Read-only.

It never reapplies anything. To act again, make a new plan and approve it.
"""

from __future__ import annotations

import datetime as _dt

from . import device, evidence, report
from .errors import AdReceiptsError, SafetyStop
from .journal import Journal
from .store import now_iso, read_json, write_json


def run(app):
    adb = app.connect("read")
    props, dev = device.identity(adb, app.home)
    run_id = getattr(app.args, "run", None)
    candidates = [run_id] if run_id else list(reversed(app.runs.all()))
    chosen = None
    for rid in candidates:
        rdir = app.home / rid
        info = read_json(rdir / "run.json") or {}
        if (rdir / "scan.json").exists() and info.get("device", {}).get("id_hash") == dev.get("id_hash"):
            chosen = rid
            break
    if not chosen:
        if run_id:
            raise SafetyStop("Run %s was made on another phone or has no scan." % run_id)
        raise AdReceiptsError("No earlier scan of this phone was found.", hint="Run: python adreceipts.py scan")
    run_dir = app.home / chosen
    last = read_json(run_dir / "scan.json")
    info = read_json(run_dir / "run.json")
    cat = app.catalog(props)
    now = evidence.collect(adb, cat)
    journal = Journal(run_dir)
    updated = info["device"].get("build_hash") != dev.get("build_hash")

    came_back, changed = [], []
    for c in journal.changes().values():
        if c["batch"] == "drill" or c["phase"] != "done":
            continue
        if c["op"] in ("disable", "uninstall"):
            st = now["packages"].get(c["target"], {}).get("state", "absent")
            if st == "enabled":
                came_back.append("%s is on again (AdReceipts turned it off in batch %s)" % (c["target"], c["batch"]))
        elif c["op"] == "dns":
            mode = now["info"].get("private_dns_mode")
            spec = now["info"].get("private_dns_specifier")
            if mode != "hostname" or spec != c["target"]:
                came_back.append("Private DNS is no longer %s (now: %s %s)" % (c["target"], mode, spec or ""))
        elif c["op"] == "setting":
            v = device.setting(adb, c["namespace"], c["key"])
            if v != c.get("value"):
                came_back.append("setting %s is %s again" % (c["target"], v))
    for name in sorted(set(last["evidence"]["packages"]) | set(now["packages"])):
        b = last["evidence"]["packages"].get(name, {}).get("state", "absent")
        a = now["packages"].get(name, {}).get("state", "absent")
        if b != a:
            changed.append("%s: %s at scan time, %s now" % (name, b, a))
    new_unknown = sorted(set(now["unknown_adlike"]) - set(last["evidence"].get("unknown_adlike", [])))

    sections = [
        {"h": "Summary", "blocks": [
            {"p": "Compared with the scan of %s (run %s)." % (last["time"], chosen)},
            {"note": "recheck changed nothing and reapplies nothing. To act again: plan, approve, apply."},
        ] + ([{"note": "The system version changed since that scan: an update was installed."}] if updated else [])},
        {"h": "Came back after AdReceipts turned it off", "blocks": [{"ul": came_back} if came_back else {"p": "Nothing came back."}]},
        {"h": "Changed since the scan", "blocks": [{"ul": changed} if changed else {"p": "No package changed state."}]},
    ]
    if new_unknown:
        sections.append({"h": "New unrecognized ad-like packages", "blocks": [{"ul": new_unknown}]})
    sections.append({"h": "What this does not prove", "blocks": [{"ul": report.LIMITS}]})
    doc = {"title": "AdReceipts recheck", "subtitle": "%s - %s" % (report.device_line(dev), now_iso()),
           "simulated": dev.get("simulated"), "sections": sections}
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    write_json(run_dir / ("recheck-%s.json" % stamp), {"time": now_iso(), "updated": updated, "came_back": came_back,
                                                       "changed": changed, "new_unknown": new_unknown})
    path = report.write(doc, run_dir, "recheck-%s" % stamp)
    app.say("Recheck (read-only) against run %s." % chosen)
    if updated:
        app.say("  The system was updated since that scan.")
    app.say("  Came back: %d" % len(came_back))
    for line in came_back:
        app.say("    - %s" % line)
    app.say("  Changed since the scan: %d" % len(changed), "Report: %s" % path)
    if came_back:
        app.say("", "Nothing was reapplied. To turn these off again: python adreceipts.py scan, then backup, drill, plan.")
    return 0
